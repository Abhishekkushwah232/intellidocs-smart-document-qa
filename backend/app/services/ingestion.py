from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.core.config import settings
from app.core.db import ensure_pool_started, pool
from app.services.chunker import chunk_by_tokens
from app.services.embeddings import embed_texts
from app.services.pdfs import extract_text_from_pdf


@dataclass(frozen=True)
class IngestionResult:
    chunks_created: int
    document_status: str


def _decode_text_bytes(file_bytes: bytes) -> str:
    # Simple decoding strategy for .txt uploads.
    return file_bytes.decode("utf-8", errors="ignore")


def ingest_document(
    *,
    user_id: str,
    document_id: uuid.UUID,
    filename: str,
    file_bytes: bytes,
    content_type: str | None,
    doc_kind: str,
) -> IngestionResult:
    """
    Extract -> chunk -> embed -> insert into pgvector-backed chunks table.
    """
    ensure_pool_started()

    pages: list[tuple[int, str]] = []
    doc_kind = doc_kind.lower()
    if doc_kind == "pdf":
        extracted = extract_text_from_pdf(file_bytes)
        pages = [(p.page_number, p.text) for p in extracted]
    elif doc_kind == "text":
        # Treat whole file as page 1
        pages = [(1, _decode_text_bytes(file_bytes))]
    else:
        raise ValueError(f"Unsupported doc_kind={doc_kind}")

    # Reduce embedding workload to avoid hitting rate limits.
    # With whitespace-based chunking, these are word counts (not real tokens).
    chunk_size_tokens = 420
    overlap_tokens = 30
    max_pages = 12
    max_total_chunks = 60
    pages = pages[:max_pages]

    all_chunks: list[tuple[int, int, str]] = []
    # (page_number, chunk_index, chunk_text)
    chunk_index = 0
    for page_number, page_text in pages:
        page_chunks = chunk_by_tokens(
            page_text,
            chunk_size_tokens=chunk_size_tokens,
            overlap_tokens=overlap_tokens,
        )
        for c in page_chunks:
            all_chunks.append((page_number, chunk_index, c.text))
            chunk_index += 1
            if len(all_chunks) >= max_total_chunks:
                break
        if len(all_chunks) >= max_total_chunks:
            break

    if not all_chunks:
        # Mark as "ready" but with zero chunks; query will return no context.
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    update documents
                    set status = 'ready'
                    where id = %s and user_id = %s
                    """,
                    (str(document_id), user_id),
                )
            conn.commit()
        return IngestionResult(chunks_created=0, document_status="ready")

    # Insert in batches to keep request time reasonable.
    batch_size = 4
    created = 0
    with pool.connection() as conn:
        with conn.cursor() as cur:
            for i in range(0, len(all_chunks), batch_size):
                batch = all_chunks[i : i + batch_size]
                # Compute embeddings for this batch.
                texts = [t for (_p, _idx, t) in batch]
                embeddings = embed_texts(texts)

                if len(embeddings) != len(batch):
                    raise RuntimeError("Embedding output size mismatch.")

                rows = []
                for (page_number, idx, content), embedding in zip(batch, embeddings):
                    chunk_id = uuid.uuid4()
                    rows.append(
                        (
                            str(chunk_id),
                            str(document_id),
                            user_id,
                            content,
                            embedding,
                            idx,
                            page_number,
                        )
                    )

                cur.executemany(
                    """
                    insert into chunks (id, document_id, user_id, content, embedding, chunk_index, page_number)
                    values (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    rows,
                )
                created += len(rows)

        conn.commit()

    # Mark document ready after successful insertion.
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update documents
                set status = 'ready'
                where id = %s and user_id = %s
                """,
                (str(document_id), user_id),
            )
        conn.commit()

    return IngestionResult(chunks_created=created, document_status="ready")

