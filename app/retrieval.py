import asyncio
import logging
from typing import Optional

from openai import AsyncOpenAI

from app.settings import settings

logger = logging.getLogger("app.retrieval")

_openai_client: Optional[AsyncOpenAI] = None


def _get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY não configurada")
    if _openai_client is None:
        kwargs: dict = {"api_key": settings.openai_api_key}
        if settings.openai_api_url:
            kwargs["base_url"] = settings.openai_api_url
        _openai_client = AsyncOpenAI(**kwargs)
    return _openai_client


async def compute_embedding(text: str) -> list[float]:
    client = _get_openai_client()
    response = await client.embeddings.create(
        model=settings.embedding_model,
        input=text,
    )
    return response.data[0].embedding


async def semantic_search(text: str, pg_conn) -> str:
    if not text or not settings.openai_api_key:
        return ""

    try:
        embedding = await compute_embedding(text)
    except Exception:
        logger.exception("Erro ao calcular embedding")
        return ""

    def fetch_docs():
        with pg_conn.cursor() as cur:
            cur.execute(
                """
                SELECT content
                FROM documents
                ORDER BY embedding <-> %s
                LIMIT 3
                """,
                (embedding,),
            )
            return cur.fetchall()

    try:
        rows = await asyncio.to_thread(fetch_docs)
    except Exception:
        logger.exception("Erro ao executar busca semântica no PostgreSQL")
        return ""

    if not rows:
        logger.info("Nenhum documento encontrado para a busca semântica")
        return ""

    return "\n\n".join(row[0] for row in rows)
