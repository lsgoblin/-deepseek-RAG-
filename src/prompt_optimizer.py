"""Prompt optimization service backed by retrieval and DeepSeek."""

from __future__ import annotations

from collections import OrderedDict
import json
import re
from typing import Any

try:
    from src.config import get_settings
    from src.llm import generate_answer
    from src.rag_pipeline import ensure_knowledge_base
    from src.retriever import retrieve_top_k
    from src.schemas import RetrievedChunk
except ModuleNotFoundError:  # pragma: no cover - script execution fallback
    from config import get_settings
    from llm import generate_answer
    from rag_pipeline import ensure_knowledge_base
    from retriever import retrieve_top_k
    from schemas import RetrievedChunk


DEFAULT_PLATFORM = "通用"


def _build_retrieval_query(
    *,
    raw_prompt: str,
    platform: str,
    style: str,
    goal: str,
) -> str:
    """Assemble a retrieval query from the optimization request."""

    parts = [
        f"原始提示词：{raw_prompt.strip()}",
        f"目标平台：{platform.strip() or DEFAULT_PLATFORM}",
    ]
    if style.strip():
        parts.append(f"风格偏好：{style.strip()}")
    if goal.strip():
        parts.append(f"优化目标：{goal.strip()}")
    return "\n".join(parts)


def _format_retrieved_chunks(retrieved_chunks: list[RetrievedChunk]) -> str:
    """Render retrieval hits into a readable context block."""

    sections: list[str] = []
    for index, item in enumerate(retrieved_chunks, start=1):
        score_text = "unknown"
        if item.score is not None:
            score_text = f"{item.score:.4f}"

        sections.append(
            "\n".join(
                [
                    f"[Reference Chunk {index}]",
                    f"Source: {item.chunk.source_doc}",
                    f"Chunk Index: {item.chunk.chunk_index}",
                    f"Similarity: {score_text}",
                    "Content:",
                    item.chunk.chunk_text,
                ]
            )
        )

    return "\n\n".join(sections)


def build_direct_optimization_prompt(
    *,
    raw_prompt: str,
    platform: str,
    style: str,
    goal: str,
) -> str:
    """Build an LLM-only prompt without retrieval context."""

    style_text = style.strip() or "未指定"
    goal_text = goal.strip() or "提升提示词的完整度、可控性与出图质量"

    return (
        "You are an expert prompt engineer for AI image generation systems.\n"
        "Improve the user's raw prompt while preserving the original subject and intent.\n"
        "Do not invent a completely different scene. Make the prompt more specific, visual, "
        "and directly usable in image-generation models.\n"
        "Return strict JSON only.\n\n"
        f"Target platform: {platform.strip() or DEFAULT_PLATFORM}\n"
        f"Style preference: {style_text}\n"
        f"Optimization goal: {goal_text}\n"
        f"Raw prompt: {raw_prompt.strip()}\n\n"
        "Return this JSON schema exactly:\n"
        "{\n"
        '  "optimized_prompt": "完整优化后的提示词",\n'
        '  "notes": ["说明补充了哪些维度", "说明压缩或强化了哪些信息"]\n'
        "}\n"
        "The `notes` field must be written in Chinese."
    )


def _build_optimization_prompt(
    *,
    raw_prompt: str,
    platform: str,
    style: str,
    goal: str,
    retrieved_chunks: list[RetrievedChunk],
) -> str:
    """Build the LLM prompt for retrieval-augmented prompt optimization."""

    context_block = _format_retrieved_chunks(retrieved_chunks)
    style_text = style.strip() or "未指定"
    goal_text = goal.strip() or "提升提示词的完整度、可控性与出图质量"

    return (
        "You are an expert prompt engineer for AI image generation systems.\n"
        "You must improve the user's prompt using the supplied reference material.\n"
        "Preserve the original subject and intent. Reuse relevant descriptive elements from the "
        "references when they help, but do not fabricate unsupported techniques or facts.\n"
        "Return strict JSON only.\n\n"
        f"Target platform: {platform.strip() or DEFAULT_PLATFORM}\n"
        f"Style preference: {style_text}\n"
        f"Optimization goal: {goal_text}\n"
        f"Raw prompt: {raw_prompt.strip()}\n\n"
        f"Reference material:\n{context_block}\n\n"
        "Return this JSON schema exactly:\n"
        "{\n"
        '  "optimized_prompt": "完整优化后的提示词",\n'
        '  "notes": ["说明补充了哪些维度", "说明为何这样改写"]\n'
        "}\n"
        "The `notes` field must be written in Chinese."
    )


def _parse_json_payload(answer_text: str) -> dict[str, Any]:
    """Extract a JSON object from LLM text output."""

    candidates = [answer_text.strip()]

    fenced_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", answer_text, re.DOTALL)
    if fenced_match:
        candidates.append(fenced_match.group(1).strip())

    start = answer_text.find("{")
    end = answer_text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(answer_text[start : end + 1].strip())

    seen: set[str] = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload

    raise ValueError("Model output is not valid JSON.")


def _normalize_notes(raw_notes: Any) -> list[str]:
    """Normalize notes into a clean string list."""

    if isinstance(raw_notes, str):
        normalized = [raw_notes.strip()]
    elif isinstance(raw_notes, list):
        normalized = [str(item).strip() for item in raw_notes if str(item).strip()]
    else:
        normalized = []

    return [item for item in normalized if item]


def parse_optimization_response(answer_text: str, fallback_prompt: str) -> tuple[str, list[str]]:
    """Parse LLM JSON output into a normalized prompt and note list."""

    try:
        payload = _parse_json_payload(answer_text)
        optimized_prompt = str(payload.get("optimized_prompt", "")).strip()
        notes = _normalize_notes(payload.get("notes"))
    except ValueError:
        optimized_prompt = answer_text.strip()
        notes = ["模型未返回标准 JSON，已直接采用原始输出文本。"]

    if not optimized_prompt:
        optimized_prompt = fallback_prompt
    if not notes:
        notes = ["模型未返回额外说明。"]

    return optimized_prompt, notes


def serialize_retrieved_chunks(retrieved_chunks: list[RetrievedChunk]) -> list[dict[str, Any]]:
    """Convert retrieved chunks into JSON-friendly dictionaries."""

    return [
        {
            "chunk_id": item.chunk.chunk_id,
            "source": item.chunk.source_doc,
            "chunk_index": item.chunk.chunk_index,
            "score": item.score,
            "text": item.chunk.chunk_text,
        }
        for item in retrieved_chunks
    ]


def retrieve_prompt_references(
    *,
    raw_prompt: str,
    platform: str = DEFAULT_PLATFORM,
    style: str = "",
    goal: str = "",
) -> tuple[str, list[RetrievedChunk], list[str]]:
    """Retrieve knowledge-base references for one optimization request."""

    settings = get_settings()
    retrieval_query = _build_retrieval_query(
        raw_prompt=raw_prompt,
        platform=platform,
        style=style,
        goal=goal,
    )
    store = ensure_knowledge_base()
    retrieved_chunks = retrieve_top_k(
        question=retrieval_query,
        store=store,
        embedding_model=settings.embedding_model,
        top_k=settings.top_k,
    )
    sources = list(
        OrderedDict.fromkeys(item.chunk.source_doc for item in retrieved_chunks)
    )
    return retrieval_query, retrieved_chunks, sources


def optimize_prompt(
    *,
    raw_prompt: str,
    platform: str = DEFAULT_PLATFORM,
    style: str = "",
    goal: str = "",
) -> dict[str, Any]:
    """Optimize an image-generation prompt using retrieval-augmented context."""

    normalized_prompt = raw_prompt.strip()
    if not normalized_prompt:
        raise ValueError("Raw prompt cannot be empty.")

    retrieval_query, retrieved_chunks, sources = retrieve_prompt_references(
        raw_prompt=normalized_prompt,
        platform=platform,
        style=style,
        goal=goal,
    )

    if not retrieved_chunks:
        return {
            "optimized_prompt": normalized_prompt,
            "notes": ["知识库未命中相关参考，当前返回原始提示词。"],
            "sources": [],
            "retrieved_chunks": [],
            "retrieval_query": retrieval_query,
        }

    prompt = _build_optimization_prompt(
        raw_prompt=normalized_prompt,
        platform=platform,
        style=style,
        goal=goal,
        retrieved_chunks=retrieved_chunks,
    )
    answer = generate_answer(prompt=prompt)
    optimized_prompt, notes = parse_optimization_response(
        answer.answer_text,
        normalized_prompt,
    )

    return {
        "optimized_prompt": optimized_prompt,
        "notes": notes,
        "sources": sources,
        "retrieved_chunks": serialize_retrieved_chunks(retrieved_chunks),
        "retrieval_query": retrieval_query,
    }
