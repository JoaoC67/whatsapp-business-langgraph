import logging
from typing import Optional, TypedDict

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from app.retrieval import semantic_search
from app.settings import settings

logger = logging.getLogger("app.pipeline")

try:
    from langgraph.graph import StateGraph, END
    HAS_LANGGRAPH = True
except Exception:
    HAS_LANGGRAPH = False

_SYSTEM_PROMPT = "Você é um assistente de atendimento para WhatsApp Business. Responda de forma clara, amigável e concisa."

_anthropic_client: Optional[AsyncAnthropic] = None
_openai_client: Optional[AsyncOpenAI] = None


class _GraphState(TypedDict):
    prompt: str
    response: str


def _get_anthropic_client() -> AsyncAnthropic:
    global _anthropic_client
    if _anthropic_client is None:
        if not settings.claude_api_key:
            raise ValueError("CLAUDE_API_KEY não configurada")
        kwargs = {"api_key": settings.claude_api_key}
        if settings.claude_api_url:
            kwargs["base_url"] = settings.claude_api_url
        _anthropic_client = AsyncAnthropic(**kwargs)
    return _anthropic_client


def _get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY não configurada")
        kwargs = {"api_key": settings.openai_api_key}
        if settings.openai_api_url:
            kwargs["base_url"] = settings.openai_api_url
        _openai_client = AsyncOpenAI(**kwargs)
    return _openai_client


async def _call_anthropic(prompt: str) -> str:
    client = _get_anthropic_client()
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


async def _call_openai(prompt: str) -> str:
    client = _get_openai_client()
    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        max_tokens=800,
        temperature=0.2,
    )
    choice = response.choices[0]
    message = getattr(choice, "message", None)
    if isinstance(message, dict):
        return message.get("content", "") or ""
    if hasattr(message, "get"):
        return message.get("content", "") or ""
    return str(choice)


async def _call_llm(prompt: str) -> str:
    if settings.claude_api_key:
        try:
            logger.info("Usando Anthropic Claude")
            return await _call_anthropic(prompt)
        except Exception as exc:
            logger.warning(f"Falha no Anthropic: {exc}")
            if settings.openai_api_key:
                logger.info("Tentando fallback OpenAI")
                return await _call_openai(prompt)
            raise

    if settings.openai_api_key:
        logger.info("Usando OpenAI")
        return await _call_openai(prompt)

    raise ValueError("Nenhuma chave de LLM configurada (CLAUDE_API_KEY ou OPENAI_API_KEY)")


async def run_langgraph(sender: str, text: str, history: list[str], redis_client, pg_conn) -> str:
    context = await semantic_search(text, pg_conn)
    prompt = build_prompt(text, history, context)

    if HAS_LANGGRAPH:
        try:
            async def llm_node(state: _GraphState) -> dict:
                response = await _call_llm(state["prompt"])
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

    return await _call_llm(prompt)


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
