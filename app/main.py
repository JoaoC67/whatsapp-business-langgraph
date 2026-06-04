import logging
import threading

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Query
import httpx
import redis.asyncio as redis
import psycopg
from pgvector.psycopg import register_vector

from app.pipeline import HAS_LANGGRAPH, run_langgraph
from app.settings import settings

app = FastAPI(title="WhatsApp Business LangGraph API")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn.error")
redis_client = redis.from_url(settings.redis_url, decode_responses=True)
pg_conn = None
_pg_lock = threading.Lock()


def get_pg_conn():
    global pg_conn
    with _pg_lock:
        if pg_conn is None:
            pg_conn = psycopg.connect(settings.postgres_dsn)
            register_vector(pg_conn)
    return pg_conn

WHATSAPP_API = f"https://graph.facebook.com/v17.0/{settings.whatsapp_phone_id}/messages"
HEADERS = {
    "Authorization": f"Bearer {settings.whatsapp_token}",
    "Content-Type": "application/json",
}

@app.get("/webhook")
async def verify_webhook(
    mode: str = Query(alias="hub.mode", default=None),
    challenge: str = Query(alias="hub.challenge", default=None),
    verify_token: str = Query(alias="hub.verify_token", default=None),
):
    if mode == "subscribe" and verify_token == settings.whatsapp_verify_token:
        return challenge
    raise HTTPException(status_code=403, detail="Invalid verification token")

@app.get("/health")
async def health():
    redis_ok = False
    postgres_ok = False

    try:
        redis_ok = await redis_client.ping()
    except Exception:
        logger.exception("Falha ao conectar com Redis")

    try:
        conn = get_pg_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            postgres_ok = cur.fetchone() == (1,)
    except Exception:
        logger.exception("Falha ao conectar com PostgreSQL")

    status = "ok" if redis_ok and postgres_ok else "degraded"
    return {"status": status, "redis": bool(redis_ok), "postgres": bool(postgres_ok)}

@app.get("/status")
async def status():
    return {
        "app": "whatsapp-business-langgraph",
        "langgraph_installed": HAS_LANGGRAPH,
        "claude_model": settings.claude_model,
        "embedding_model": settings.embedding_model,
        "session_ttl_seconds": settings.session_ttl_seconds,
        "max_history_messages": settings.max_history_messages,
    }

@app.post("/webhook")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        payload = await request.json()
    except Exception:
        logger.exception("Falha ao ler payload do webhook")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    entry = payload.get("entry", [{}])[0]
    changes = entry.get("changes", [{}])[0]
    value = changes.get("value", {})
    messages = value.get("messages", [])

    if not messages:
        return {"status": "no_message"}

    message = messages[0]
    sender = message.get("from")
    text = message.get("text", {}).get("body")
    if not sender or not text:
        return {"status": "ignored"}

    message_id = message.get("id")
    if message_id:
        dedup_key = f"whatsapp:msg:{message_id}"
        if not await redis_client.set(dedup_key, "1", nx=True, ex=300):
            return {"status": "duplicate"}

    background_tasks.add_task(handle_message, sender, text)
    return {"status": "accepted"}

async def handle_message(sender: str, text: str):
    session_key = f"whatsapp:{sender}:history"
    response_text = "Desculpa, não consegui processar isso no momento."

    try:
        history = await redis_client.lrange(session_key, 0, -1)
        response_text = await run_langgraph(sender, text, history, redis_client, get_pg_conn())
    except Exception:
        logger.exception("Erro ao processar a mensagem de WhatsApp")

    if not response_text:
        response_text = "Desculpa, não consegui processar isso no momento."

    try:
        await redis_client.rpush(session_key, f"user: {text}", f"assistant: {response_text}")
        await redis_client.expire(session_key, settings.session_ttl_seconds)
    except Exception:
        logger.exception("Erro ao atualizar histórico no Redis")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                WHATSAPP_API,
                headers=HEADERS,
                json={
                    "messaging_product": "whatsapp",
                    "to": sender,
                    "type": "text",
                    "text": {"body": response_text},
                },
            )
            resp.raise_for_status()
        except httpx.HTTPError:
            logger.exception("Falha ao enviar resposta para o WhatsApp")
