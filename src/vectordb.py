"""Vector database utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from src.schemas import RetrievedChunk, TextChunk
except ModuleNotFoundError:  # pragma: no cover - script execution fallback
    from schemas import RetrievedChunk, TextChunk


COLLECTION_NAME = "rag_documents"


def _get_chroma_collection(persist_dir: Path) -> Any:
    """Create or load the default Chroma collection."""

    try:
        import chromadb
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on runtime env
        raise RuntimeError("Missing dependency `chromadb`. Install requirements first.") from exc

    persist_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist_dir))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def _ensure_supported_store(db_type: str) -> str:
    """Normalize and validate the vector-store backend type."""

    normalized = db_type.strip().lower()
    if normalized == "faiss":
        raise NotImplementedError("FAISS is reserved but not implemented yet. Use `chroma`.")
    if normalized != "chroma":
        raise ValueError(f"Unsupported vector DB type: {db_type}")
    return normalized


def _serialize_metadata(chunk: TextChunk) -> dict[str, str | int | float | bool]:
    """Convert chunk metadata into Chroma-compatible scalar values."""

    metadata: dict[str, str | int | float | bool] = {
        "chunk_id": chunk.chunk_id,
        "source_doc": chunk.source_doc,
        "chunk_index": chunk.chunk_index,
    }

    for key, value in chunk.metadata.items():
        if isinstance(value, (str, int, float, bool)):
            metadata[key] = value
        elif value is not None:
            metadata[key] = str(value)

    return metadata


def create_vector_store(db_type: str, persist_dir: Path) -> Any:
    """Create a vector-store backend instance."""

    _ensure_supported_store(db_type)
    return _get_chroma_collection(persist_dir)


def load_vector_store(db_type: str, persist_dir: Path) -> Any:
    """Load an existing vector-store backend instance."""

    _ensure_supported_store(db_type)
    return _get_chroma_collection(persist_dir)


def index_chunks(
    store: Any,
    chunks: list[TextChunk],
    embeddings: list[list[float]],
) -> None:
    """Write chunks and embeddings into the vector store."""

    if not chunks:
        return
    if len(chunks) != len(embeddings):
        raise ValueError("The number of chunks and embeddings must match.")

    store.upsert(
        ids=[chunk.chunk_id for chunk in chunks],
        embeddings=embeddings,
        documents=[chunk.chunk_text for chunk in chunks],
        metadatas=[_serialize_metadata(chunk) for chunk in chunks],
    )


def search_similar(
    store: Any,
    query_embedding: list[float],
    top_k: int,
) -> list[RetrievedChunk]:
    """Search the vector store for the most similar chunks."""

    if top_k <= 0:
        raise ValueError("top_k must be greater than 0.")
    if store.count() == 0:
        return []

    result = store.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]
    ids = result.get("ids", [[]])[0]

    retrieved: list[RetrievedChunk] = []
    for chunk_id, document, metadata, distance in zip(ids, documents, metadatas, distances):
        chunk = TextChunk(
            chunk_id=metadata.get("chunk_id", chunk_id),
            source_doc=metadata.get("source_doc", "unknown"),
            chunk_text=document,
            chunk_index=int(metadata.get("chunk_index", 0)),
            metadata={
                key: value
                for key, value in metadata.items()
                if key not in {"chunk_id", "source_doc", "chunk_index"}
            },
        )
        score = None if distance is None else 1.0 / (1.0 + float(distance))
        retrieved.append(RetrievedChunk(chunk=chunk, score=score))

    return retrieved
