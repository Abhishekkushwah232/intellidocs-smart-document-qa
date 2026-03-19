from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    text: str


def chunk_by_tokens(text: str, *, chunk_size_tokens: int, overlap_tokens: int) -> list[Chunk]:
    """
    Pragmatic chunking function.

    Note: We intentionally avoid tokenizers like `tiktoken` because they may require a Rust
    toolchain on some environments. For this assignment, whitespace chunking with overlap
    is accurate enough for RAG retrieval + citations.
    """
    text = (text or "").strip()
    if not text:
        return []

    # Use whitespace as "token" proxy.
    words = text.split()
    if len(words) <= chunk_size_tokens:
        return [Chunk(text=text)]

    chunks: list[Chunk] = []
    step = max(chunk_size_tokens - overlap_tokens, 1)
    for start in range(0, len(words), step):
        end = start + chunk_size_tokens
        word_slice = words[start:end]
        if not word_slice:
            break
        chunks.append(Chunk(text=" ".join(word_slice)))
        if end >= len(words):
            break

    return chunks

