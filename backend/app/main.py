"""
FastAPI application entry: CORS, routers, health check.

CORS is permissive (`*`) because the SPA uses `Authorization: Bearer` only
(no cookies). Tighten `allow_origins` for production hardening if required.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.documents import router as documents_router
from app.api.routes.query import router as query_router

from app.core.config import settings

_log = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Log AI config at startup (no secrets). Helps verify Railway/.env after adding Gemini."""
    prov = settings.llm_provider.lower()
    if prov == "gemini":
        if settings.gemini_api_key:
            _log.info("IntelliDocs: LLM primary=gemini model=%s", settings.gemini_model)
        else:
            _log.warning(
                "IntelliDocs: LLM_PROVIDER=gemini but GEMINI_API_KEY is empty — "
                "will try fallbacks (grok/anthropic/openai) or extractive answer."
            )
    else:
        _log.info("IntelliDocs: LLM primary=%s", prov)
    _log.info(
        "IntelliDocs: embeddings provider=%s dim=%s",
        settings.embeddings_provider,
        settings.embeddings_dim,
    )
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="IntelliDocs API", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        # The frontend calls the API with an `Authorization: Bearer ...` header (no cookies).
        # In production, allow all origins to avoid hard-to-debug origin-mismatch issues
        # caused by environment variable formatting differences.
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    app.include_router(documents_router, prefix="/documents", tags=["documents"])
    app.include_router(query_router, prefix="/query", tags=["query"])

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()

