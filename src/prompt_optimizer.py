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
        f"目标平台：{platform.strip() or '通用'}",
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
        score = "未知"
        if item.score is not None:
            score = f"{item.score:.4f}"
        sections.append(
            "\n".join(
                [
                    f"[参考片段 {index}]",
                    f"来源：{item.chunk.source_doc}",
                    f"chunk_index：{item.chunk.chunk_index}",
                    f"相似度：{score}",
                    "内容：",
                    item.chunk.chunk_text,
                ]
            )
        )
    return "\n\n".join(sections)


def _build_optimization_prompt(
    *,
    raw_prompt: str,
    platform: str,
    style: str,
    goal: str,
    retrieved_chunks: list[RetrievedChunk],
) -> str:
    """Build the LLM prompt for prompt optimization."""

    context_block = _format_retrieved_chunks(retrieved_chunks)
    style_text = style.strip() or "未指定"
    goal_text = goal.strip() or "提升提示词质量与可用性"

    return (
        "你是一个专门帮助用户优化 AI 生图提示词的助手。"
        "你必须仅根据提供的参考内容完成优化，不要编造参考内容中没有出现的专有技巧。"
        "输出结果要尽量适合直接投喂图像模型，默认优先给出结构化、紧凑、可执行的英文提示词。"
        "如果参考内容不足，也要保留用户原始主体，不要偏离主题。\n\n"
        f"【目标平台】\n{platform.strip() or '通用'}\n\n"
        f"【风格偏好】\n{style_text}\n\n"
        f"【优化目标】\n{goal_text}\n\n"
        f"【原始提示词】\n{raw_prompt.strip()}\n\n"
        f"【参考内容】\n{context_block}\n\n"
        "请返回严格 JSON，不要输出 JSON 之外的任何内容：\n"
        "{\n"
        '  "optimized_prompt": "优化后的完整提示词",\n'
        '  "notes": ["说明第1点", "说明第2点", "说明第3点"]\n'
        "}\n"
        "其中 notes 需要用中文，简洁说明你补充或改写了哪些维度，例如主体、场景、镜头、光影、材质、风格、构图。"
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


def optimize_prompt(
    *,
    raw_prompt: str,
    platform: str = "通用",
    style: str = "",
    goal: str = "",
) -> dict[str, Any]:
    """Optimize an image-generation prompt using retrieval-augmented context."""

    normalized_prompt = raw_prompt.strip()
    if not normalized_prompt:
        raise ValueError("Raw prompt cannot be empty.")

    settings = get_settings()
    retrieval_query = _build_retrieval_query(
        raw_prompt=normalized_prompt,
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

    if not retrieved_chunks:
        return {
            "optimized_prompt": normalized_prompt,
            "notes": ["知识库未命中相关提示词参考，当前返回原始提示词。"],
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

    try:
        payload = _parse_json_payload(answer.answer_text)
        optimized_prompt = str(payload.get("optimized_prompt", "")).strip()
        notes = _normalize_notes(payload.get("notes"))
    except ValueError:
        optimized_prompt = answer.answer_text.strip()
        notes = ["模型未返回标准 JSON，已直接返回原始优化结果文本。"]

    if not optimized_prompt:
        optimized_prompt = normalized_prompt
    if not notes:
        notes = ["模型未返回优化说明。"]

    return {
        "optimized_prompt": optimized_prompt,
        "notes": notes,
        "sources": sources,
        "retrieved_chunks": [
            {
                "chunk_id": item.chunk.chunk_id,
                "source": item.chunk.source_doc,
                "chunk_index": item.chunk.chunk_index,
                "score": item.score,
                "text": item.chunk.chunk_text,
            }
            for item in retrieved_chunks
        ],
        "retrieval_query": retrieval_query,
    }
