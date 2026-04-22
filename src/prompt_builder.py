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
        score = "未知"
        if item.score is not None:
            score = f"{item.score:.4f}"

        sections.append(
            "\n".join(
                [
                    f"[片段 {index}]",
                    f"来源：{item.chunk.source_doc}",
                    f"相似度：{score}",
                    "内容：",
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
        context_block = "无可用参考内容。"
    else:
        context_block = _format_retrieved_chunks(retrieved_chunks)

    return (
        "你是一个严谨的课程项目问答助手。请仅根据提供的参考内容回答用户问题。"
        "如果参考内容不足以支持回答，请直接回答“根据现有资料无法回答”，"
        "不要编造事实，不要补充参考内容之外的信息。\n\n"
        f"【参考内容】\n{context_block}\n\n"
        f"【用户问题】\n{normalized_question}\n\n"
        "请输出：\n"
        "1. 简洁准确的回答；\n"
        "2. 回答后用“来源：”列出引用到的文档名。"
    )
