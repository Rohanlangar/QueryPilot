"""
QueryPilot — Application Configuration

Centralized settings loaded from environment variables / .env file.
Uses Pydantic Settings for validation and type coercion.
"""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable loading."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── App Database ──────────────────────────────────────────
    app_db_url: str = "sqlite+aiosqlite:///./querypilot.db"

    # ── Security ──────────────────────────────────────────────
    secret_key: str = "change-me-to-a-random-secret-key-at-least-32-chars"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    encryption_key: str = ""  # Fernet key for encrypting DB credentials

    # ── LLM Configuration ─────────────────────────────────────
    llm_mode: str = "online"  # "online" or "offline"
    llm_api_url: str = "https://api.openai.com/v1/chat/completions"
    llm_api_key: str = ""
    llm_model: str = "gpt-4"

    # ── Query Safety ──────────────────────────────────────────
    max_query_rows: int = 10000
    query_timeout_seconds: int = 30

    # ── Caching ───────────────────────────────────────────────
    cache_ttl_seconds: int = 3600

    # ── Server ────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]


# Singleton settings instance
settings = Settings()
