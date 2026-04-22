"""Document loading utilities."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Iterable

try:
    from src.schemas import SourceDocument
except ModuleNotFoundError:  # pragma: no cover - script execution fallback
    from schemas import SourceDocument


LOGGER = logging.getLogger(__name__)


SUPPORTED_EXTENSIONS = (".txt", ".md", ".pdf", ".docx")


def discover_documents(
    data_dir: Path,
    max_docs: int | None = None,
    extensions: Iterable[str] = SUPPORTED_EXTENSIONS,
) -> list[Path]:
    """Return candidate document paths from the data directory."""

    normalized_extensions = {ext.lower() for ext in extensions}
    discovered = sorted(
        file_path
        for file_path in data_dir.rglob("*")
        if file_path.is_file() and file_path.suffix.lower() in normalized_extensions
    )

    if max_docs is not None:
        return discovered[:max_docs]
    return discovered


def _build_doc_id(file_path: Path) -> str:
    """Create a stable document identifier from the file path."""

    digest = hashlib.md5(str(file_path.resolve()).encode("utf-8")).hexdigest()[:12]
    return f"{file_path.stem}-{digest}"


def _read_text_file(file_path: Path) -> str:
    """Read plain-text content with a few common encoding fallbacks."""

    candidate_encodings = ("utf-8", "utf-8-sig", "gb18030")
    last_error: UnicodeDecodeError | None = None

    for encoding in candidate_encodings:
        try:
            return file_path.read_text(encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc

    if last_error is not None:
        raise last_error
    return ""


def _read_pdf_file(file_path: Path) -> str:
    """Extract text from a PDF file."""

    try:
        from pypdf import PdfReader
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on runtime env
        raise RuntimeError("Missing dependency `pypdf`. Install requirements first.") from exc

    reader = PdfReader(str(file_path))
    return "\n".join((page.extract_text() or "").strip() for page in reader.pages).strip()


def _read_docx_file(file_path: Path) -> str:
    """Extract text from a DOCX file."""

    try:
        from docx import Document
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on runtime env
        raise RuntimeError(
            "Missing dependency `python-docx`. Install requirements first."
        ) from exc

    document = Document(str(file_path))
    return "\n".join(paragraph.text for paragraph in document.paragraphs).strip()


def load_document(file_path: Path) -> SourceDocument:
    """Load one document and normalize it as `SourceDocument`."""

    suffix = file_path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {file_path.suffix}")

    if suffix in {".txt", ".md"}:
        content = _read_text_file(file_path)
    elif suffix == ".pdf":
        content = _read_pdf_file(file_path)
    else:
        content = _read_docx_file(file_path)

    return SourceDocument(
        doc_id=_build_doc_id(file_path),
        source_path=file_path,
        source_name=file_path.name,
        file_type=suffix.lstrip("."),
        content=content.strip(),
        metadata={"source": file_path.name},
    )


def load_documents(data_dir: Path, max_docs: int | None = None) -> list[SourceDocument]:
    """Load all supported documents from a knowledge-base directory."""

    loaded_documents: list[SourceDocument] = []
    for file_path in discover_documents(data_dir=data_dir, max_docs=max_docs):
        try:
            loaded_documents.append(load_document(file_path))
        except Exception as exc:  # pragma: no cover - exercised by runtime failures
            LOGGER.warning("Skipping document %s: %s", file_path, exc)

    return loaded_documents
