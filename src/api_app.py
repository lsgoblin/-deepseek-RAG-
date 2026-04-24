"""FastAPI application for the prompt optimization website."""

from __future__ import annotations

from pathlib import Path

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import FileResponse
    from pydantic import BaseModel, Field
except ModuleNotFoundError as exc:  # pragma: no cover - depends on runtime env
    raise RuntimeError(
        "Missing dependencies `fastapi` and `pydantic`. Install requirements first."
    ) from exc

try:
    from src.build_vector_store import build_vector_store_summary
    from src.config import get_settings
    from src.loaders import discover_documents
    from src.prompt_optimizer import optimize_prompt
    from src.vectordb import load_vector_store
except ModuleNotFoundError:  # pragma: no cover - script execution fallback
    from build_vector_store import build_vector_store_summary
    from config import get_settings
    from loaders import discover_documents
    from prompt_optimizer import optimize_prompt
    from vectordb import load_vector_store


HTML_FILE = Path(__file__).resolve().parent / "deepseek_rag_homepage_prototype.html"

app = FastAPI(
    title="AI Image Prompt Optimizer",
    description="DeepSeek + RAG powered prompt optimization website backend.",
    version="0.1.0",
)


class OptimizeRequest(BaseModel):
    """Request payload for prompt optimization."""

    raw_prompt: str = Field(..., min_length=1)
    platform: str = Field(default="通用")
    style: str = Field(default="")
    goal: str = Field(default="")


def _get_store_count() -> int:
    """Return the current vector-store document count."""

    settings = get_settings()
    store = load_vector_store(settings.vector_db_type, settings.vector_db_dir)
    if hasattr(store, "count"):
        return int(store.count())
    return 0


def _build_status_payload() -> dict[str, object]:
    """Collect runtime status for the frontend dashboard."""

    settings = get_settings()
    documents = discover_documents(
        data_dir=settings.data_dir,
        max_docs=settings.max_docs,
    )

    vector_count = 0
    vector_error: str | None = None
    try:
        vector_count = _get_store_count()
    except Exception as exc:  # pragma: no cover - runtime environment dependent
        vector_error = str(exc)

    return {
        "app_title": "AI 生图提示词优化平台",
        "has_api_key": bool(settings.deepseek_api_key),
        "deepseek_model": settings.deepseek_model,
        "embedding_model": settings.embedding_model,
        "vector_db_type": settings.vector_db_type,
        "data_dir": str(settings.data_dir),
        "vector_db_dir": str(settings.vector_db_dir),
        "document_count": len(documents),
        "documents": [path.name for path in documents[:20]],
        "vector_count": vector_count,
        "vector_error": vector_error,
        "top_k": settings.top_k,
        "temperature": settings.temperature,
    }


@app.get("/")
def serve_homepage() -> FileResponse:
    """Serve the current homepage prototype."""

    if not HTML_FILE.exists():
        raise HTTPException(status_code=404, detail="Homepage prototype file not found.")
    return FileResponse(HTML_FILE)


@app.get("/api/status")
def get_status() -> dict[str, object]:
    """Return knowledge-base and runtime status for the frontend."""

    try:
        return _build_status_payload()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/optimize")
def optimize_prompt_api(payload: OptimizeRequest) -> dict[str, object]:
    """Optimize a prompt and return retrieval evidence."""

    try:
        return optimize_prompt(
            raw_prompt=payload.raw_prompt,
            platform=payload.platform,
            style=payload.style,
            goal=payload.goal,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/rebuild-kb")
def rebuild_knowledge_base() -> dict[str, object]:
    """Build or refresh the prompt knowledge base."""

    settings = get_settings()
    try:
        summary = build_vector_store_summary(
            data_dir=settings.data_dir,
            vector_db_dir=settings.vector_db_dir,
            vector_db_type=settings.vector_db_type,
            embedding_model=settings.embedding_model,
            max_docs=settings.max_docs,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "message": "知识库已完成构建或刷新。",
        "summary": summary,
    }
