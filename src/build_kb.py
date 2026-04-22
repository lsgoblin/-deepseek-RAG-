"""Knowledge-base build entrypoint skeleton."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

try:
    from src.config import get_settings
    from src.loaders import load_documents
    from src.splitter import split_documents
except ModuleNotFoundError:  # pragma: no cover - script execution fallback
    from config import get_settings
    from loaders import load_documents
    from splitter import split_documents


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the knowledge-base build command."""

    settings = get_settings()
    parser = argparse.ArgumentParser(description="Build the knowledge-base preview.")
    parser.add_argument("--data-dir", type=Path, default=settings.data_dir)
    parser.add_argument("--max-docs", type=int, default=settings.max_docs)
    parser.add_argument("--chunk-size", type=int, default=settings.chunk_size)
    parser.add_argument("--chunk-overlap", type=int, default=settings.chunk_overlap)
    parser.add_argument(
        "--summary-out",
        type=Path,
        default=settings.experiment_results_dir / "build_kb_summary.json",
    )
    return parser.parse_args()


def build_summary(
    *,
    data_dir: Path,
    max_docs: int,
    chunk_size: int,
    chunk_overlap: int,
) -> dict[str, object]:
    """Load documents, split them, and return a summary payload."""

    documents = load_documents(data_dir=data_dir, max_docs=max_docs)
    chunks = split_documents(
        documents=documents,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    return {
        "data_dir": str(data_dir),
        "documents_loaded": len(documents),
        "chunks_created": len(chunks),
        "documents": [
            {
                "doc_id": document.doc_id,
                "source_name": document.source_name,
                "file_type": document.file_type,
                "content_length": len(document.content),
            }
            for document in documents
        ],
        "chunk_preview": [asdict(chunk) for chunk in chunks[:5]],
    }


def main() -> None:
    """Run the knowledge-base build command."""

    args = parse_args()
    summary = build_summary(
        data_dir=args.data_dir,
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
    print(f"Chunks created: {summary['chunks_created']}")
    print(f"Summary written to: {args.summary_out}")


if __name__ == "__main__":
    main()
