"""Export the Jimeng prompt spreadsheet into a final Markdown knowledge-base file."""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from src.loaders import _extract_xlsx_rows
except ModuleNotFoundError:  # pragma: no cover - script execution fallback
    from loaders import _extract_xlsx_rows


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the export command."""

    parser = argparse.ArgumentParser(
        description="Export a raw Jimeng prompt spreadsheet into Markdown."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def build_markdown(input_path: Path) -> str:
    """Render the spreadsheet as a final Markdown knowledge-base document."""

    rows = _extract_xlsx_rows(input_path)
    if not rows:
        raise RuntimeError(f"No valid rows found in {input_path}.")

    first_row_keys = list(rows[0]["row_data"].keys())
    sequence_key = first_row_keys[0] if first_row_keys else "sequence"
    field_order = first_row_keys[1:]

    unique_counts: dict[str, int] = {}
    for field in field_order:
        values = {
            str(item["row_data"].get(field, "")).strip()
            for item in rows
            if str(item["row_data"].get(field, "")).strip()
        }
        unique_counts[field] = len(values)

    lines = [
        "# Jimeng Prompt Knowledge Base",
        "",
        f"- source_file: `{input_path.name}`",
        "- format: normalized_markdown",
        f"- record_count: {len(rows)}",
        "",
        "## Notes",
        "",
        "- This file is the final knowledge-base artifact exported from the raw spreadsheet.",
        "- The raw spreadsheet should stay under `data/raw/` as source material only.",
        "- Each record keeps the original columns and adds one reusable combined prompt.",
        "",
        "## Field Stats",
        "",
    ]

    for field in field_order:
        lines.append(f"- {field}: {unique_counts[field]} unique values")

    lines.extend(["", "## Records", ""])

    for index, item in enumerate(rows, start=1):
        row_data = item["row_data"]
        sequence_value = row_data.get(sequence_key, index)
        combined_prompt = "，".join(
            str(row_data.get(field, "")).strip()
            for field in field_order
            if str(row_data.get(field, "")).strip()
        )

        lines.append(f"### Record {index:03d}")
        lines.append("")
        lines.append(f"- {sequence_key}: {sequence_value}")
        lines.append(f"- source_sheet: {item['sheet_name']}")
        for field in field_order:
            lines.append(f"- {field}: {str(row_data.get(field, '')).strip()}")
        lines.append(f"- combined_prompt: {combined_prompt}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def main() -> None:
    """Run the export command."""

    args = parse_args()
    markdown = build_markdown(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
