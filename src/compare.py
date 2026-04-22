"""Comparison experiment interfaces."""

from __future__ import annotations

from src.schemas import LLMAnswer, RetrievedChunk


def run_comparison(
    question: str,
) -> dict[str, str | LLMAnswer | list[RetrievedChunk]]:
    """Run LLM-only, retrieval-only, and RAG modes for one question."""

    raise NotImplementedError("Comparison experiments will be implemented in S16.")
