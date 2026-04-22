"""Shared data structures for the RAG pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class SourceDocument:
    """Normalized representation of one loaded source document."""

    doc_id: str
    source_path: Path
    source_name: str
    file_type: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TextChunk:
    """A text segment ready for embedding and retrieval."""

    chunk_id: str
    source_doc: str
    chunk_text: str
    chunk_index: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RetrievedChunk:
    """A retrieval hit containing one chunk and its optional score."""

    chunk: TextChunk
    score: float | None = None


@dataclass(slots=True)
class LLMAnswer:
    """Standardized LLM output with sources and optional raw payload."""

    answer_text: str
    sources: list[str] = field(default_factory=list)
    raw_response: dict[str, Any] = field(default_factory=dict)

