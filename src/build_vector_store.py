"""Build and persist the final vector store from the local knowledge-base sources."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from src.config import get_settings
    from src.embedder import embed_chunks
    from src.loaders import load_documents
    from src.splitter import split_documents
    from src.vectordb import create_vector_store, load_vector_store, index_chunks
except ModuleNotFoundError:  # pragma: no cover - script execution fallback
    from config import get_settings
    from embedder import embed_chunks
    from loaders import load_documents
    from splitter import split_documents
    from vectordb import create_vector_store, load_vector_store, index_chunks


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the vector-store build command."""

    settings = get_settings()
    parser = argparse.ArgumentParser(description="Build the final vector store.")
    parser.add_argument("--data-dir", type=Path, default=settings.data_dir)
    parser.add_argument("--vector-db-dir", type=Path, default=settings.vector_db_dir)
    parser.add_argument("--vector-db-type", type=str, default=settings.vector_db_type)
    parser.add_argument("--embedding-model", type=str, default=settings.embedding_model)
    parser.add_argument("--max-docs", type=int, default=settings.max_docs)
    parser.add_argument("--chunk-size", type=int, default=settings.chunk_size)
    parser.add_argument("--chunk-overlap", type=int, default=settings.chunk_overlap)
    parser.add_argument(
        "--summary-out",
        type=Path,
        default=settings.experiment_results_dir / "build_vector_store_summary.json",
    )
    return parser.parse_args()


def _get_store_count(store: object) -> int:
    """Return the collection count when supported by the backend."""

    if hasattr(store, "count"):
        return int(store.count())
    return 0


def build_vector_store_summary(
    *,
    data_dir: Path,
    vector_db_dir: Path,
    vector_db_type: str,
    embedding_model: str,
    max_docs: int,
    chunk_size: int,
    chunk_overlap: int,
) -> dict[str, object]:
    """Build the vector store from the current knowledge-base sources."""

    documents = load_documents(data_dir=data_dir, max_docs=max_docs)
    if not documents:
        raise RuntimeError(f"No supported documents found in {data_dir}.")

    chunks = split_documents(
        documents=documents,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    if not chunks:
        raise RuntimeError("No chunks were generated from the loaded documents.")

    embeddings = embed_chunks(chunks=chunks, model_name=embedding_model)
    store = create_vector_store(vector_db_type, vector_db_dir)
    index_chunks(store=store, chunks=chunks, embeddings=embeddings)

    return {
        "data_dir": str(data_dir),
        "vector_db_dir": str(vector_db_dir),
        "vector_db_type": vector_db_type,
        "embedding_model": embedding_model,
        "documents_loaded": len(documents),
        "chunks_indexed": len(chunks),
        "store_count": _get_store_count(load_vector_store(vector_db_type, vector_db_dir)),
        "document_sources": [document.source_name for document in documents],
    }


def main() -> None:
    """Run the vector-store build command."""

    args = parse_args()
    summary = build_vector_store_summary(
        data_dir=args.data_dir,
        vector_db_dir=args.vector_db_dir,
        vector_db_type=args.vector_db_type,
        embedding_model=args.embedding_model,
        max_docs=args.max_docs,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )

    args.summary_out.parent.mkdir(parents=True, exist_ok=True)
    args.summary_out.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Documents loaded: {summary['documents_loaded']}")
    print(f"Chunks indexed: {summary['chunks_indexed']}")
    print(f"Store count: {summary['store_count']}")
    print(f"Vector store dir: {summary['vector_db_dir']}")
    print(f"Summary written to: {args.summary_out}")


if __name__ == "__main__":
    main()
