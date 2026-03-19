from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.documents import router as documents_router
from app.api.routes.query import router as query_router

from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title="IntelliDocs API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
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

