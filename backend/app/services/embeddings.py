"""
Text embeddings: local sentence-transformers only (384-dim MiniLM; matches pgvector schema).
"""
from __future__ import annotations

from functools import lru_cache

from app.core.config import settings


@lru_cache(maxsize=1)
def _load_local_model():
    try:
        from sentence_transformers import SentenceTransformer
    except Exception as e:
        raise RuntimeError(
            "sentence-transformers is required for embeddings but isn't installed."
        ) from e

    return SentenceTransformer(settings.embeddings_local_model)


def _embed_local(texts: list[str]) -> list[list[float]]:
    model = _load_local_model()
    embeddings = model.encode(
        texts,
        normalize_embeddings=False,
        show_progress_bar=False,
    )

    out: list[list[float]] = []
    for vec in embeddings:
        out.append([float(x) for x in vec])
    return out


def embed_texts(texts: list[str]) -> list[list[float]]:
    return _embed_local(texts)

