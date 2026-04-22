"""Embedding utilities."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

try:
    from src.schemas import TextChunk
except ModuleNotFoundError:  # pragma: no cover - script execution fallback
    from schemas import TextChunk


@lru_cache(maxsize=4)
def load_embedding_model(model_name: str) -> Any:
    """Load an embedding backend instance by model name."""

    try:
        from sentence_transformers import SentenceTransformer
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on runtime env
        raise RuntimeError(
            "Missing dependency `sentence-transformers`. Install requirements first."
        ) from exc

    return SentenceTransformer(model_name)


def _normalize_vectors(raw_vectors: Any) -> list[list[float]]:
    """Convert model output vectors into plain Python float lists."""

    if hasattr(raw_vectors, "tolist"):
        normalized = raw_vectors.tolist()
    else:
        normalized = raw_vectors

    if not normalized:
        return []

    if isinstance(normalized[0], (int, float)):
        return [[float(value) for value in normalized]]

    return [[float(value) for value in vector] for vector in normalized]


def embed_chunks(chunks: list[TextChunk], model_name: str) -> list[list[float]]:
    """Convert text chunks into vector embeddings."""

    if not chunks:
        return []

    model = load_embedding_model(model_name)
    texts = [chunk.chunk_text for chunk in chunks]
    embeddings = model.encode(
        texts,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return _normalize_vectors(embeddings)


def embed_query(question: str, model_name: str) -> list[float]:
    """Convert a user question into one query embedding."""

    normalized_question = question.strip()
    if not normalized_question:
        raise ValueError("Question cannot be empty.")

    model = load_embedding_model(model_name)
    embedding = model.encode(
        normalized_question,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return _normalize_vectors(embedding)[0]
