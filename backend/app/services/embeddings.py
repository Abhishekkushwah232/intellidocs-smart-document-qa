"""
Text embeddings: OpenAI (hosted) with retries / quota fallback, or local sentence-transformers.
"""
from __future__ import annotations

from functools import lru_cache

import time
import requests

from app.core.config import settings


@lru_cache(maxsize=1)
def _load_local_model():
    try:
        from sentence_transformers import SentenceTransformer
    except Exception as e:
        raise RuntimeError(
            "sentence-transformers is required for EMBEDDINGS_PROVIDER=local, but it isn't installed. "
            "Either install it or set EMBEDDINGS_PROVIDER=openai."
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
    if settings.embeddings_provider == "local":
        return _embed_local(texts)

    if settings.embeddings_provider == "openai":
        # If OpenAI key isn't configured, fall back to local embeddings.
        if not settings.openai_api_key:
            return _embed_local(texts)

        url = "https://api.openai.com/v1/embeddings"
        headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
        payload = {
            "model": "text-embedding-3-small",
            "input": texts,
            "dimensions": settings.embeddings_dim,
        }

        # Retry for rate limits (429) to keep ingestion reliable.
        # Also retries transient 5xx errors.
        max_attempts = 6
        backoff_seconds = 1.0
        last_error: Exception | None = None
        last_status: int | None = None
        last_body: str | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=90)
                last_status = resp.status_code
                try:
                    last_body = resp.text[:500]
                except Exception:
                    last_body = None

                if resp.status_code == 429:
                    # If quota is exhausted, retrying won't help; fallback to local.
                    try:
                        j = resp.json()
                        code = (j.get("error") or {}).get("code")
                        err_type = (j.get("error") or {}).get("type")
                    except Exception:
                        code = None
                        err_type = None

                    if code == "insufficient_quota" or err_type == "insufficient_quota":
                        return _embed_local(texts)

                    # Respect server-provided retry time when available.
                    retry_after = resp.headers.get("Retry-After")
                    wait_s = backoff_seconds
                    if retry_after:
                        try:
                            wait_s = float(retry_after)
                        except ValueError:
                            pass

                    # Capture last error details for better error reporting.
                    last_error = RuntimeError(f"OpenAI embeddings 429 rate limit. body={last_body}")

                    time.sleep(wait_s)
                    backoff_seconds *= 2
                    continue

                # Some providers may return a JSON error payload even with non-429s.
                # Handle "insufficient_quota" explicitly by falling back to local.
                if resp.status_code in (400, 401, 403, 404):
                    try:
                        j = resp.json()
                        code = (j.get("error") or {}).get("code")
                        err_type = (j.get("error") or {}).get("type")
                    except Exception:
                        code = None
                        err_type = None
                    if code == "insufficient_quota" or err_type == "insufficient_quota":
                        return _embed_local(texts)

                resp.raise_for_status()
                data = resp.json()["data"]
                # OpenAI returns embeddings in the same order as input
                return [[float(x) for x in item["embedding"]] for item in data]
            except Exception as e:
                last_error = e
                if attempt == max_attempts:
                    break
                time.sleep(backoff_seconds)
                backoff_seconds *= 2

        raise RuntimeError(
            f"Embedding request failed after retries. last_status={last_status}, last_error={last_error}, last_body={last_body}"
        ) from last_error

    raise RuntimeError(f"Unknown EMBEDDINGS_PROVIDER={settings.embeddings_provider}")

