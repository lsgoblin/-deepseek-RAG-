"""Retrieval orchestration."""

from __future__ import annotations

from typing import Any

try:
    from src.embedder import embed_query
    from src.schemas import RetrievedChunk
    from src.vectordb import search_similar
except ModuleNotFoundError:  # pragma: no cover - script execution fallback
    from embedder import embed_query
    from schemas import RetrievedChunk
    from vectordb import search_similar


def retrieve_top_k(
    question: str,
    store: Any,
    embedding_model: str,
    top_k: int,
) -> list[RetrievedChunk]:
    """Retrieve the most relevant chunks for one user question."""

    query_embedding = embed_query(question=question, model_name=embedding_model)
    return search_similar(store=store, query_embedding=query_embedding, top_k=top_k)
