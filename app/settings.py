from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    redis_url: str = Field(..., env="REDIS_URL")
    postgres_dsn: str = Field(..., env="POSTGRES_DSN")

    whatsapp_phone_id: str = Field(..., env="WHATSAPP_PHONE_ID")
    whatsapp_token: str = Field(..., env="WHATSAPP_TOKEN")
    whatsapp_verify_token: str = Field(..., env="WHATSAPP_VERIFY_TOKEN")

    claude_api_key: str = Field(..., env="CLAUDE_API_KEY")
    claude_api_url: Optional[str] = Field(None, env="CLAUDE_API_URL")
    claude_model: str = Field("claude-sonnet-4-6", env="CLAUDE_MODEL")

    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    openai_api_url: Optional[str] = Field(None, env="OPENAI_API_URL")
    embedding_model: str = Field("text-embedding-3-large", env="EMBEDDING_MODEL")

    session_ttl_seconds: int = Field(3600, env="SESSION_TTL_SECONDS")
    max_history_messages: int = Field(6, env="MAX_HISTORY_MESSAGES")

    class Config:
        env_file = Path(__file__).resolve().parent.parent / ".env"

settings = Settings()
