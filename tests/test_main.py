import os

os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("POSTGRES_DSN", "postgresql://postgres:password@localhost:5432/whatsapp")
os.environ.setdefault("WHATSAPP_PHONE_ID", "phone_id")
os.environ.setdefault("WHATSAPP_TOKEN", "token")
os.environ.setdefault("WHATSAPP_VERIFY_TOKEN", "verify_token")
os.environ.setdefault("CLAUDE_API_KEY", "claude_key")
os.environ.setdefault("CLAUDE_API_URL", "https://api.anthropic.com")
os.environ.setdefault("OPENAI_API_KEY", "openai_key")

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_status_endpoint():
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == "whatsapp-business-langgraph"
    assert "langgraph_installed" in data
    assert "claude_model" in data
    assert "embedding_model" in data
    assert "session_ttl_seconds" in data
    assert "max_history_messages" in data


def test_health_endpoint_returns_degraded_when_unavailable():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "redis" in data
    assert "postgres" in data
    assert data["status"] in {"ok", "degraded"}
