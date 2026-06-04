import logging
from typing import Optional, TypedDict

from anthropic import AsyncAnthropic

from app.retrieval import semantic_search
from app.settings import settings

logger = logging.getLogger("app.pipeline")

try:
    from langgraph.graph import StateGraph, END
    HAS_LANGGRAPH = True
except Exception:
    HAS_LANGGRAPH = False

_SYSTEM_PROMPT = "Você é um assistente de atendimento para WhatsApp Business. Responda de forma clara, amigável e concisa."

_client: Optional[AsyncAnthropic] = None


class _GraphState(TypedDict):
    prompt: str
    response: str


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=settings.claude_api_key)
    return _client


async def _call_claude(prompt: str) -> str:
    client = _get_client()
    resp = await client.messages.create(
        model=settings.claude_model,
        max_tokens=800,
        system=[{
            "type": "text",
            "text": _SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text


async def run_langgraph(sender: str, text: str, history: list[str], redis_client, pg_conn) -> str:
    context = await semantic_search(text, pg_conn)
    prompt = build_prompt(text, history, context)

    if HAS_LANGGRAPH:
        try:
            async def llm_node(state: _GraphState) -> dict:
                response = await _call_claude(state["prompt"])
                return {"response": response}

            graph = StateGraph(_GraphState)
            graph.add_node("llm", llm_node)
            graph.set_entry_point("llm")
            graph.add_edge("llm", END)
            compiled = graph.compile()
            result = await compiled.ainvoke({"prompt": prompt, "response": ""})
            return result["response"]
        except Exception:
            logger.exception("LangGraph falhou, usando fallback direto")

    return await _call_claude(prompt)


def build_prompt(text: str, history: list[str], context: str) -> str:
    def sanitize_history(raw_history: list[str]) -> list[tuple[str, str]]:
        pairs: list[tuple[str, str]] = []
        for entry in raw_history:
            if not isinstance(entry, str):
                continue
            entry = entry.strip()
            if entry.lower().startswith("user:") or entry.lower().startswith("usuario:"):
                pairs.append(("user", entry.split(":", 1)[1].strip()))
            elif entry.lower().startswith("assistant:") or entry.lower().startswith("assistente:"):
                pairs.append(("assistant", entry.split(":", 1)[1].strip()))
        return pairs

    def format_history(pairs: list[tuple[str, str]], max_messages: int) -> str:
        if not pairs:
            return ""
        sliced = pairs[-max_messages:]
        out_lines: list[str] = []
        for role, content in sliced:
            if role == "user":
                out_lines.append(f"Usuário: {content}")
            else:
                out_lines.append(f"Assistente: {content}")
        return "\n".join(out_lines)

    prompt_parts = []

    if context:
        prompt_parts.append(f"Contexto relevante:\n{context}\n")

    sanitized = sanitize_history(history or [])
    history_text = format_history(sanitized, settings.max_history_messages)
    if history_text:
        prompt_parts.append(f"Histórico de conversa:\n{history_text}\n")

    prompt_parts.append(f"Usuário: {text}\nAssistente:")
    return "\n\n".join(prompt_parts)
