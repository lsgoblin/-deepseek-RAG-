"""End-to-end RAG pipeline."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

try:
    from src.config import get_settings
    from src.embedder import embed_chunks
    from src.llm import generate_answer
    from src.loaders import load_documents
    from src.prompt_builder import build_rag_prompt
    from src.retriever import retrieve_top_k
    from src.schemas import LLMAnswer, RetrievedChunk
    from src.splitter import split_documents
    from src.vectordb import create_vector_store, index_chunks, load_vector_store
except ModuleNotFoundError:  # pragma: no cover - script execution fallback
    from config import get_settings
    from embedder import embed_chunks
    from llm import generate_answer
    from loaders import load_documents
    from prompt_builder import build_rag_prompt
    from retriever import retrieve_top_k
    from schemas import LLMAnswer, RetrievedChunk
    from splitter import split_documents
    from vectordb import create_vector_store, index_chunks, load_vector_store


def _get_store_count(store: Any) -> int:
    """Return the number of indexed chunks in the vector store."""

    if not hasattr(store, "count"):
        return 0
    return int(store.count())


def ensure_knowledge_base() -> Any:
    """Create the vector store if needed and index local documents on first use."""

    settings = get_settings()
    store = load_vector_store(settings.vector_db_type, settings.vector_db_dir)
    if _get_store_count(store) > 0:
        return store

    documents = load_documents(data_dir=settings.data_dir, max_docs=settings.max_docs)
    if not documents:
        raise RuntimeError(f"No supported documents found in {settings.data_dir}.")

    chunks = split_documents(
        documents=documents,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    if not chunks:
        raise RuntimeError("No chunks were generated from the loaded documents.")

    embeddings = embed_chunks(chunks=chunks, model_name=settings.embedding_model)
    store = create_vector_store(settings.vector_db_type, settings.vector_db_dir)
    index_chunks(store=store, chunks=chunks, embeddings=embeddings)
    return store


def answer_question(question: str) -> tuple[LLMAnswer, list[RetrievedChunk]]:
    """Run the end-to-end RAG flow for one question."""

    normalized_question = question.strip()
    if not normalized_question:
        raise ValueError("Question cannot be empty.")

    settings = get_settings()
    store = ensure_knowledge_base()
    retrieved_chunks = retrieve_top_k(
        question=normalized_question,
        store=store,
        embedding_model=settings.embedding_model,
        top_k=settings.top_k,
    )

    if not retrieved_chunks:
        return LLMAnswer(answer_text="根据现有资料无法回答"), []

    prompt = build_rag_prompt(
        question=normalized_question,
        retrieved_chunks=retrieved_chunks,
    )
    answer = generate_answer(prompt=prompt)
    answer.sources = list(
        OrderedDict.fromkeys(item.chunk.source_doc for item in retrieved_chunks)
    )
    return answer, retrieved_chunks
