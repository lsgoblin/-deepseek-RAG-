"""Comparison experiment helpers for prompt optimization."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from src.llm import generate_answer
    from src.prompt_optimizer import (
        DEFAULT_PLATFORM,
        build_direct_optimization_prompt,
        optimize_prompt,
        parse_optimization_response,
        retrieve_prompt_references,
        serialize_retrieved_chunks,
    )
except ModuleNotFoundError:  # pragma: no cover - script execution fallback
    from llm import generate_answer
    from prompt_optimizer import (
        DEFAULT_PLATFORM,
        build_direct_optimization_prompt,
        optimize_prompt,
        parse_optimization_response,
        retrieve_prompt_references,
        serialize_retrieved_chunks,
    )


DEFAULT_EXPERIMENT_CASES = [
    {
        "label": "人物类提示词优化",
        "raw_prompt": "赛博朋克女战士站在雨夜街头",
        "platform": "即梦",
        "style": "电影感，霓虹，高细节",
        "goal": "增强人物造型、场景氛围和镜头语言",
    },
    {
        "label": "场景类提示词优化",
        "raw_prompt": "清晨云海中的古风山寺",
        "platform": "Midjourney",
        "style": "东方美学，空灵，层次丰富",
        "goal": "强化空间层次、光影和环境细节",
    },
    {
        "label": "产品海报类提示词优化",
        "raw_prompt": "一款高端香水的广告海报",
        "platform": "通用",
        "style": "商业摄影，极简高级",
        "goal": "突出材质、品牌感和广告构图",
    },
]


def _safe_execute(callback: Any) -> dict[str, Any]:
    """Run one mode and capture runtime failures as structured output."""

    try:
        payload = callback()
    except Exception as exc:  # pragma: no cover - depends on runtime state
        return {
            "status": "error",
            "error": str(exc),
        }

    if isinstance(payload, dict):
        payload.setdefault("status", "success")
        return payload

    return {
        "status": "success",
        "value": payload,
    }


def _run_llm_only_mode(
    *,
    raw_prompt: str,
    platform: str,
    style: str,
    goal: str,
) -> dict[str, Any]:
    """Run the prompt optimizer without retrieval context."""

    prompt = build_direct_optimization_prompt(
        raw_prompt=raw_prompt,
        platform=platform,
        style=style,
        goal=goal,
    )
    answer = generate_answer(prompt=prompt)
    optimized_prompt, notes = parse_optimization_response(answer.answer_text, raw_prompt)
    return {
        "optimized_prompt": optimized_prompt,
        "notes": notes,
        "sources": [],
        "retrieved_chunks": [],
    }


def _run_retrieval_only_mode(
    *,
    raw_prompt: str,
    platform: str,
    style: str,
    goal: str,
) -> dict[str, Any]:
    """Return retrieval evidence without calling the LLM."""

    retrieval_query, retrieved_chunks, sources = retrieve_prompt_references(
        raw_prompt=raw_prompt,
        platform=platform,
        style=style,
        goal=goal,
    )

    if not retrieved_chunks:
        notes = ["知识库未检索到相关片段，无法提供参考依据。"]
    else:
        notes = [
            f"共检索到 {len(retrieved_chunks)} 个相关片段。",
            "该模式只展示可追溯的知识片段，不生成最终优化提示词。",
        ]

    return {
        "retrieval_query": retrieval_query,
        "notes": notes,
        "sources": sources,
        "retrieved_chunks": serialize_retrieved_chunks(retrieved_chunks),
    }


def _run_rag_mode(
    *,
    raw_prompt: str,
    platform: str,
    style: str,
    goal: str,
) -> dict[str, Any]:
    """Run the full retrieval-augmented optimization mode."""

    return optimize_prompt(
        raw_prompt=raw_prompt,
        platform=platform,
        style=style,
        goal=goal,
    )


def run_mode(
    mode: str,
    *,
    raw_prompt: str,
    platform: str = DEFAULT_PLATFORM,
    style: str = "",
    goal: str = "",
) -> dict[str, Any]:
    """Run one prompt-optimization mode and normalize the output."""

    normalized_prompt = raw_prompt.strip()
    if not normalized_prompt:
        raise ValueError("Raw prompt cannot be empty.")

    normalized_platform = platform or DEFAULT_PLATFORM

    handlers = {
        "llm_only": lambda: _run_llm_only_mode(
            raw_prompt=normalized_prompt,
            platform=normalized_platform,
            style=style,
            goal=goal,
        ),
        "retrieval_only": lambda: _run_retrieval_only_mode(
            raw_prompt=normalized_prompt,
            platform=normalized_platform,
            style=style,
            goal=goal,
        ),
        "rag": lambda: _run_rag_mode(
            raw_prompt=normalized_prompt,
            platform=normalized_platform,
            style=style,
            goal=goal,
        ),
    }

    if mode not in handlers:
        raise ValueError(f"Unsupported mode: {mode}")

    return _safe_execute(handlers[mode])


def run_comparison(
    raw_prompt: str,
    *,
    platform: str = DEFAULT_PLATFORM,
    style: str = "",
    goal: str = "",
) -> dict[str, Any]:
    """Run LLM-only, retrieval-only, and RAG modes for one prompt."""

    normalized_prompt = raw_prompt.strip()
    if not normalized_prompt:
        raise ValueError("Raw prompt cannot be empty.")

    payload = {
        "input": {
            "raw_prompt": normalized_prompt,
            "platform": platform or DEFAULT_PLATFORM,
            "style": style,
            "goal": goal,
        },
        "modes": {
            "llm_only": run_mode(
                "llm_only",
                raw_prompt=normalized_prompt,
                platform=platform,
                style=style,
                goal=goal,
            ),
            "retrieval_only": run_mode(
                "retrieval_only",
                raw_prompt=normalized_prompt,
                platform=platform,
                style=style,
                goal=goal,
            ),
            "rag": run_mode(
                "rag",
                raw_prompt=normalized_prompt,
                platform=platform,
                style=style,
                goal=goal,
            ),
        },
    }
    return payload


def run_experiment_suite(
    cases: list[dict[str, str]] | None = None,
) -> list[dict[str, Any]]:
    """Run comparison experiments for a batch of prompt cases."""

    normalized_cases = cases or DEFAULT_EXPERIMENT_CASES
    results: list[dict[str, Any]] = []
    for case in normalized_cases:
        result = run_comparison(
            case["raw_prompt"],
            platform=case.get("platform", DEFAULT_PLATFORM),
            style=case.get("style", ""),
            goal=case.get("goal", ""),
        )
        result["label"] = case.get("label", case["raw_prompt"])
        results.append(result)
    return results


def _build_markdown_report(results: list[dict[str, Any]]) -> str:
    """Render comparison results into a screenshot-friendly Markdown report."""

    sections = [
        "# Prompt Optimization Comparison Results",
        "",
        "This report compares `LLM-only`, `Retrieval-only`, and `RAG` modes for the same inputs.",
        "",
    ]

    for index, item in enumerate(results, start=1):
        sections.append(f"## Case {index}: {item.get('label', 'Untitled')}")
        sections.append("")
        input_payload = item["input"]
        sections.append(f"- Raw prompt: {input_payload['raw_prompt']}")
        sections.append(f"- Platform: {input_payload['platform']}")
        sections.append(f"- Style: {input_payload['style'] or '未指定'}")
        sections.append(f"- Goal: {input_payload['goal'] or '未指定'}")
        sections.append("")

        for mode_name, mode_payload in item["modes"].items():
            sections.append(f"### {mode_name}")
            sections.append("")
            sections.append(f"- Status: {mode_payload.get('status', 'unknown')}")
            if mode_payload.get("error"):
                sections.append(f"- Error: {mode_payload['error']}")
                sections.append("")
                continue

            optimized_prompt = mode_payload.get("optimized_prompt")
            if optimized_prompt:
                sections.append(f"- Optimized prompt: {optimized_prompt}")

            retrieval_query = mode_payload.get("retrieval_query")
            if retrieval_query:
                sections.append(f"- Retrieval query: `{retrieval_query}`")

            notes = mode_payload.get("notes") or []
            if notes:
                sections.append("- Notes:")
                sections.extend(f"  - {note}" for note in notes)

            sources = mode_payload.get("sources") or []
            if sources:
                sections.append(f"- Sources: {', '.join(sources)}")

            retrieved_chunks = mode_payload.get("retrieved_chunks") or []
            if retrieved_chunks:
                top_chunk = retrieved_chunks[0]
                sections.append(f"- Top chunk source: {top_chunk['source']}")
                sections.append(
                    f"- Top chunk preview: {top_chunk['text'][:180].replace(chr(10), ' ')}..."
                )

            sections.append("")

    return "\n".join(sections).strip() + "\n"


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for batch comparison runs."""

    parser = argparse.ArgumentParser(description="Run prompt optimization comparisons.")
    parser.add_argument("--prompt", type=str, help="One raw prompt to compare.")
    parser.add_argument("--platform", type=str, default=DEFAULT_PLATFORM)
    parser.add_argument("--style", type=str, default="")
    parser.add_argument("--goal", type=str, default="")
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--markdown-out", type=Path)
    parser.add_argument(
        "--sample-suite",
        action="store_true",
        help="Run the built-in three-case experiment suite.",
    )
    return parser.parse_args()


def main() -> None:
    """Run comparison experiments from the command line."""

    args = parse_args()

    if args.sample_suite or not args.prompt:
        results = run_experiment_suite()
    else:
        results = [
            run_comparison(
                args.prompt,
                platform=args.platform,
                style=args.style,
                goal=args.goal,
            )
        ]

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(results, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    if args.markdown_out:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(
            _build_markdown_report(results),
            encoding="utf-8",
        )

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
