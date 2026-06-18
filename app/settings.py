from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        extra="ignore",
    )

    redis_url: str = "redis://localhost:6379/0"
    postgres_dsn: str = ""
    whatsapp_phone_id: str = ""
    whatsapp_token: str = ""
    whatsapp_verify_token: str = "changeme"
    claude_api_key: str = ""
    claude_api_url: Optional[str] = None
    claude_model: str = "claude-sonnet-4-6"
    openai_api_key: Optional[str] = None
    openai_api_url: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-large"
    session_ttl_seconds: int = 3600
    max_history_messages: int = 6


settings = Settings()
