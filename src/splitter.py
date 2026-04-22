"""Text splitting utilities."""

from __future__ import annotations

try:
    from src.schemas import SourceDocument, TextChunk
except ModuleNotFoundError:  # pragma: no cover - script execution fallback
    from schemas import SourceDocument, TextChunk


def split_document(
    document: SourceDocument,
    chunk_size: int,
    chunk_overlap: int,
) -> list[TextChunk]:
    """Split one loaded document into chunk records."""

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0.")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap cannot be negative.")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size.")

    normalized_text = document.content.strip()
    if not normalized_text:
        return []

    chunks: list[TextChunk] = []
    step = chunk_size - chunk_overlap
    start = 0
    chunk_index = 0

    while start < len(normalized_text):
        end = start + chunk_size
        chunk_text = normalized_text[start:end].strip()
        if chunk_text:
            chunks.append(
                TextChunk(
                    chunk_id=f"{document.doc_id}-chunk-{chunk_index:04d}",
                    source_doc=document.source_name,
                    chunk_text=chunk_text,
                    chunk_index=chunk_index,
                    metadata={
                        "doc_id": document.doc_id,
                        "source_path": str(document.source_path),
                        "file_type": document.file_type,
                    },
                )
            )
            chunk_index += 1

        start += step

    return chunks


def split_documents(
    documents: list[SourceDocument],
    chunk_size: int,
    chunk_overlap: int,
) -> list[TextChunk]:
    """Split multiple documents into a flat chunk list."""

    all_chunks: list[TextChunk] = []
    for document in documents:
        all_chunks.extend(
            split_document(
                document=document,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
        )
    return all_chunks
