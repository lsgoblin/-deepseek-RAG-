"""Prompt construction utilities."""

from __future__ import annotations

try:
    from src.schemas import RetrievedChunk
except ModuleNotFoundError:  # pragma: no cover - script execution fallback
    from schemas import RetrievedChunk


def _format_retrieved_chunks(retrieved_chunks: list[RetrievedChunk]) -> str:
    """Render retrieved chunks into a readable prompt context block."""

    sections: list[str] = []
    for index, item in enumerate(retrieved_chunks, start=1):
        score_text = "unknown"
        if item.score is not None:
            score_text = f"{item.score:.4f}"

        sections.append(
            "\n".join(
                [
                    f"[Chunk {index}]",
                    f"Source: {item.chunk.source_doc}",
                    f"Similarity: {score_text}",
                    "Content:",
                    item.chunk.chunk_text,
                ]
            )
        )

    return "\n\n".join(sections)


def build_rag_prompt(question: str, retrieved_chunks: list[RetrievedChunk]) -> str:
    """Assemble a standard RAG prompt from the question and retrieved context."""

    normalized_question = question.strip()
    if not normalized_question:
        raise ValueError("Question cannot be empty.")

    if not retrieved_chunks:
        context_block = "No reference content available."
    else:
        context_block = _format_retrieved_chunks(retrieved_chunks)

    return (
        "You are a rigorous course-project QA assistant.\n"
        "Answer the user only from the supplied reference content.\n"
        "If the references do not contain enough information, reply with "
        '"根据现有资料无法回答" and do not fabricate details.\n\n'
        f"Reference content:\n{context_block}\n\n"
        f"User question:\n{normalized_question}\n\n"
        "Output requirements:\n"
        "1. Give a concise and accurate answer.\n"
        "2. End with a `来源：...` line that lists the cited source names."
    )
