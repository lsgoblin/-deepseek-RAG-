"""Minimal CLI entrypoint for prompt optimization and comparison."""

from __future__ import annotations

import argparse
import json
from typing import Any

try:
    from src.compare import run_comparison
    from src.prompt_optimizer import DEFAULT_PLATFORM, optimize_prompt
except ModuleNotFoundError:  # pragma: no cover - script execution fallback
    from compare import run_comparison
    from prompt_optimizer import DEFAULT_PLATFORM, optimize_prompt


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(
        description="Prompt optimization CLI for the DeepSeek + RAG course project."
    )
    parser.add_argument("--prompt", type=str, help="Raw prompt to optimize.")
    parser.add_argument("--platform", type=str, default=DEFAULT_PLATFORM)
    parser.add_argument("--style", type=str, default="")
    parser.add_argument("--goal", type=str, default="")
    parser.add_argument(
        "--mode",
        choices=("rag", "compare"),
        default="rag",
        help="Choose standard RAG optimization or three-mode comparison.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the raw JSON payload instead of formatted text.",
    )
    return parser.parse_args()


def _print_retrieved_chunks(retrieved_chunks: list[dict[str, Any]]) -> None:
    """Render source snippets in a readable CLI format."""

    if not retrieved_chunks:
        print("未返回检索片段。")
        return

    print("检索片段：")
    for index, chunk in enumerate(retrieved_chunks, start=1):
        score = chunk.get("score")
        score_text = "unknown" if score is None else f"{score:.4f}"
        snippet = str(chunk.get("text", "")).replace("\n", " ").strip()
        print(f"{index}. {chunk.get('source', 'unknown')} | score={score_text}")
        print(f"   {snippet[:180]}")


def _print_rag_result(payload: dict[str, Any]) -> None:
    """Render one standard optimization result."""

    print("\n优化结果：")
    print(payload.get("optimized_prompt", ""))
    print("\n说明：")
    for note in payload.get("notes", []):
        print(f"- {note}")

    sources = payload.get("sources") or []
    print("\n来源：")
    if sources:
        print(", ".join(sources))
    else:
        print("无")

    print("")
    _print_retrieved_chunks(payload.get("retrieved_chunks") or [])


def _print_compare_result(payload: dict[str, Any]) -> None:
    """Render three-mode comparison output."""

    print("\n输入：")
    print(payload["input"]["raw_prompt"])

    for mode_name, mode_payload in payload["modes"].items():
        print(f"\n[{mode_name}]")
        if mode_payload.get("status") == "error":
            print(f"错误：{mode_payload.get('error', 'unknown error')}")
            continue

        optimized_prompt = mode_payload.get("optimized_prompt")
        if optimized_prompt:
            print("优化结果：")
            print(optimized_prompt)

        notes = mode_payload.get("notes") or []
        if notes:
            print("说明：")
            for note in notes:
                print(f"- {note}")

        sources = mode_payload.get("sources") or []
        if sources:
            print(f"来源：{', '.join(sources)}")

        retrieved_chunks = mode_payload.get("retrieved_chunks") or []
        if retrieved_chunks:
            _print_retrieved_chunks(retrieved_chunks)


def _interactive_loop(mode: str, platform: str, style: str, goal: str) -> None:
    """Run a minimal interactive CLI session."""

    print("DeepSeek + RAG Prompt Optimizer CLI")
    print("输入空行或 `exit` 退出。")

    while True:
        raw_prompt = input("\n请输入原始提示词> ").strip()
        if not raw_prompt or raw_prompt.lower() in {"exit", "quit"}:
            return

        try:
            if mode == "compare":
                payload = run_comparison(
                    raw_prompt,
                    platform=platform,
                    style=style,
                    goal=goal,
                )
                _print_compare_result(payload)
            else:
                payload = optimize_prompt(
                    raw_prompt=raw_prompt,
                    platform=platform,
                    style=style,
                    goal=goal,
                )
                _print_rag_result(payload)
        except Exception as exc:  # pragma: no cover - depends on runtime state
            print(f"运行失败：{exc}")


def main() -> None:
    """Run the user-facing CLI entrypoint."""

    args = parse_args()

    if not args.prompt:
        _interactive_loop(args.mode, args.platform, args.style, args.goal)
        return

    if args.mode == "compare":
        payload = run_comparison(
            args.prompt,
            platform=args.platform,
            style=args.style,
            goal=args.goal,
        )
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            _print_compare_result(payload)
        return

    payload = optimize_prompt(
        raw_prompt=args.prompt,
        platform=args.platform,
        style=args.style,
        goal=args.goal,
    )
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        _print_rag_result(payload)


if __name__ == "__main__":
    main()
