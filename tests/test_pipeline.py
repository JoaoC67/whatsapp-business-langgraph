import os

os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("POSTGRES_DSN", "postgresql://postgres:password@localhost:5432/whatsapp")
os.environ.setdefault("WHATSAPP_PHONE_ID", "phone_id")
os.environ.setdefault("WHATSAPP_TOKEN", "token")
os.environ.setdefault("WHATSAPP_VERIFY_TOKEN", "verify_token")
os.environ.setdefault("CLAUDE_API_KEY", "claude_key")
os.environ.setdefault("CLAUDE_API_URL", "https://api.anthropic.com")
os.environ.setdefault("OPENAI_API_KEY", "openai_key")

from app.pipeline import build_prompt


def test_build_prompt_includes_relevant_context():
    history = [
        "user: oi",
        "assistant: olá",
        "user: como vai?",
        "assistant: bem",
    ]
    prompt = build_prompt("Qual é o status?", history, "Dados importantes")

    assert "Contexto relevante:" in prompt
    assert "Dados importantes" in prompt
    assert "Histórico de conversa:" in prompt
    assert "Usuário: oi" in prompt
    assert "Assistente: olá" in prompt
    assert "Usuário: como vai?" in prompt
    assert "Assistente: bem" in prompt
    assert prompt.strip().endswith("Assistente:")


def test_build_prompt_truncates_long_history():
    history = [
        "user: u1",
        "assistant: a1",
        "user: u2",
        "assistant: a2",
        "user: u3",
        "assistant: a3",
        "user: u4",
        "assistant: a4",
    ]

    prompt = build_prompt("Pergunta final", history, "")

    assert "Usuário: u1" not in prompt
    assert "Assistente: a1" not in prompt
    assert "Usuário: u2" in prompt
    assert "Assistente: a2" in prompt
    assert "Usuário: u4" in prompt


def test_build_prompt_sanitizes_portuguese_history_labels():
    history = ["Usuario: bom dia", "assistente: boa tarde"]
    prompt = build_prompt("Oi", history, "")

    assert "Usuário: bom dia" in prompt
    assert "Assistente: boa tarde" in prompt
