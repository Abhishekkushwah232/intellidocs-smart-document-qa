from __future__ import annotations

from pathlib import Path

import re
from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration from environment / `.env` — see `backend/.env.example` (Gemini + local embeddings only)."""

    supabase_url: str
    supabase_anon_key: str
    supabase_service_key: str
    supabase_storage_bucket: str = "documents"

    # Supabase JWT secret (Settings > Auth > JWT Secret)
    jwt_secret: str

    # Postgres connection string (Supabase Dashboard > Database > Connection string)
    database_url: str

    # Embeddings: local sentence-transformers only (384-dim; no paid embedding API).
    embeddings_provider: str = "local"
    embeddings_dim: int = 384
    embeddings_local_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    rag_top_k: int = 6

    # Answer generation: Google Gemini only (Google AI Studio API key).
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"

    # Default for local/dev; override with FRONTEND_URL in production (Vercel URL).
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

    @field_validator("embeddings_provider", mode="before")
    @classmethod
    def _embeddings_local_only(cls, v: object) -> str:
        s = str(v).strip().lower()
        if s != "local":
            raise ValueError(
                "This build only supports EMBEDDINGS_PROVIDER=local (no OpenAI embedding API). "
                "Remove EMBEDDINGS_PROVIDER=openai from your environment or set it to local."
            )
        return "local"

    @field_validator("database_url", mode="before")
    @classmethod
    def _ensure_sslmode(cls, v: object) -> str:
        # Supabase requires SSL in hosted environments; if a pasted connection
        # string is missing sslmode, Postgres connections will fail at runtime.
        s = str(v).strip()
        if "sslmode=" in s.lower():
            return s
        if "?" in s:
            return f"{s}&sslmode=require"
        return f"{s}?sslmode=require"

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

