from __future__ import annotations

from pathlib import Path

import re
from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    supabase_url: str
    supabase_anon_key: str
    supabase_service_key: str
    supabase_storage_bucket: str = "documents"

    # Supabase JWT secret (Settings > Auth > JWT Secret)
    jwt_secret: str

    # Postgres connection string (Supabase Dashboard > Database > Connection string)
    database_url: str

    anthropic_api_key: str | None = None

    # Embeddings
    # Use hosted embeddings by default (faster + fewer installation issues on Python 3.13)
    embeddings_provider: str = "openai"  # "local" | "openai"
    embeddings_dim: int = 384
    embeddings_local_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    openai_api_key: str | None = None

    # LLM
    llm_provider: str = "grok"  # "grok" | "anthropic" | "openai"
    claude_model: str = "claude-sonnet-4-6"
    rag_top_k: int = 6
    # Fallback LLM if Anthropic fails (e.g., insufficient credits).
    openai_chat_model: str = "gpt-4o-mini"

    # xAI Grok (useful when Anthropic/OpenAI quotas are exhausted).
    grok_api_key: str | None = None
    grok_model: str = "grok-4-0709"

    frontend_url: str = "https://intellidocs-smart-document-qa.vercel.app"

    # Upload constraints
    max_upload_mb: int = 10

    @field_validator("frontend_url", mode="before")
    @classmethod
    def _normalize_frontend_url(cls, v: object) -> str:
        # Railway env values sometimes include trailing whitespace/newlines and
        # can include a trailing slash, which would break exact CORS origin matching.
        s = str(v)
        # Remove whitespace anywhere in the string (Railway UI may wrap values with hidden newlines).
        s = re.sub(r"\s+", "", s)
        return s.strip().rstrip("/")

    model_config = SettingsConfigDict(extra="ignore")

def _pick_env_path() -> Path:
    """
    Pick the correct backend `.env` even when the folder name contains characters
    that can get normalized differently across processes.
    """
    candidates: list[Path] = []

    # Prefer `.env` from where uvicorn is started (usually backend/).
    candidates.append(Path.cwd() / ".env")

    # Also try the `.env` next to this code (backend/.env).
    candidates.append(Path(__file__).resolve().parents[2] / ".env")

    # Finally, tolerate different parent depth if needed.
    candidates.append(Path(__file__).resolve().parents[3] / ".env")

    def _looks_real(p: Path) -> bool:
        if not p.exists():
            return False
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return False
        if "SUPABASE_URL=" not in txt:
            return False
        # Avoid placeholder envs.
        return "example.supabase.co" not in txt

    for c in candidates:
        if _looks_real(c):
            return c

    # Fallback: first existing candidate.
    for c in candidates:
        if c.exists():
            return c

    # Last resort: pretend `.env` is in CWD.
    return Path.cwd() / ".env"


_env_path = _pick_env_path()
load_dotenv(dotenv_path=_env_path, override=True)

settings = Settings()

