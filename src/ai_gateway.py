"""Strict Mock AI contracts and deterministic phase 2 gateway."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import ConfigDict, Field

from .ai_prompts import DIAGNOSIS_PROMPT_VERSION, PATCH_PROMPT_VERSION, SPEC_PROMPT_VERSION
from .iteracanvas_models import Criterion, StrictModel


class MissingQuestion(StrictModel):
    question_id: str
    question: str
    affects: list[str] = Field(default_factory=list)
    required: bool = False


class Inference(StrictModel):
    field: str
    value: Any
    confidence: str
    reason: str


class SpecExtractionResult(StrictModel):
    context: dict[str, Any] = Field(default_factory=dict)
    criteria: list[Criterion] = Field(default_factory=list)
    missing_questions: list[MissingQuestion] = Field(default_factory=list)
    inferences: list[Inference] = Field(default_factory=list)


class Evidence(StrictModel):
    description: str
    region: str


class DiagnosisItem(StrictModel):
    item_id: str
    criterion_id: str | None = None
    kind: Literal["criterion", "observation"]
    verdict: Literal["pass", "fail", "uncertain", "not_applicable"]
    evidence: Evidence
    severity: Literal["low", "medium", "high"]
    confidence: Literal["low", "medium", "high"]
    possible_causes: list[str] = Field(default_factory=list)
    violates_confirmed_hard_constraint: bool = False


class DiagnosisResult(StrictModel):
    summary: str
    items: list[DiagnosisItem] = Field(default_factory=list)
    observations: list[DiagnosisItem] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)


class PromptChange(StrictModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    operation: Literal["add", "remove", "replace"]
    from_value: str | None = Field(default=None, alias="from")
    to: str | None = None
    reason: str
    diagnosis_item_ids: list[str] = Field(default_factory=list)


class ParameterChange(StrictModel):
    name: str
    old_value: Any = None
    new_value: Any = None
    operation: Literal["add", "replace", "remove", "keep"]


class PatchResult(StrictModel):
    prompt_changes: list[PromptChange] = Field(default_factory=list)
    parameter_changes: list[ParameterChange] = Field(default_factory=list)
    keep_unchanged: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    side_effects: list[str] = Field(default_factory=list)
    merged_prompt: str | None = None
    merged_params: dict[str, Any] = Field(default_factory=dict)
    base_prompt_missing: bool = False


# Fixed JSON-shaped fixtures keep mock calls contract-compatible with a future provider.
MOCK_SPEC_FIXTURE = json.dumps(
    {
        "context": {"purpose": "电商主图"},
        "criteria": [
            {
                "criterion_id": "crt_fixture",
                "category": "subject",
                "statement": "主体清晰",
                "importance": "undecided",
                "source": "ai_inference",
                "status": "pending",
                "verification_mode": "visual",
            }
        ],
        "missing_questions": [],
        "inferences": [],
    },
    ensure_ascii=False,
)
MOCK_DIAGNOSIS_FIXTURE = json.dumps(
    {
        "summary": "整体主体正确，但有一项要求待修复。",
        "items": [
            {
                "item_id": "diag_fixture",
                "criterion_id": "crt_fixture",
                "kind": "criterion",
                "verdict": "fail",
                "evidence": {"description": "主体边缘模糊", "region": "画面中央"},
                "severity": "high",
                "confidence": "high",
                "possible_causes": ["模拟夹具中的固定问题"],
                "violates_confirmed_hard_constraint": True,
            }
        ],
        "observations": [],
        "uncertainties": [],
    },
    ensure_ascii=False,
)
MOCK_PATCH_FIXTURE = json.dumps(
    {
        "prompt_changes": [],
        "parameter_changes": [],
        "keep_unchanged": [],
        "conflicts": [],
        "side_effects": [],
        "merged_prompt": None,
        "merged_params": {},
        "base_prompt_missing": False,
    },
    ensure_ascii=False,
)


def extract_spec(task_text: str, reference_images: list[dict[str, Any]] | None = None) -> SpecExtractionResult:
    """Return the same shape a real spec extractor will return in phase 4."""
    result = SpecExtractionResult.model_validate_json(MOCK_SPEC_FIXTURE)
    if task_text.strip():
        result.context = {"description": task_text.strip()}
    return result


def diagnose_candidate(
    spec: Any,
    candidate: Any,
    references: list[dict[str, Any]] | None = None,
    generation_context: dict[str, Any] | None = None,
) -> DiagnosisResult:
    """Deterministically fail the first requirement in round 1, then pass it."""
    criteria = list(spec.criteria)
    round_no = int((generation_context or {}).get("round_no", 1))
    items: list[DiagnosisItem] = []
    for index, criterion in enumerate(criteria):
        evaluated = criterion.status == "confirmed"
        failed = index == 0 and round_no == 1 and evaluated
        verdict = "fail" if failed else ("pass" if evaluated else "uncertain")
        items.append(
            DiagnosisItem(
                item_id=f"diag_{candidate.id}_{index + 1}",
                criterion_id=criterion.criterion_id,
                kind="criterion",
                verdict=verdict,
                evidence=Evidence(
                    description=(
                        "模拟诊断发现该要求需要修复"
                        if failed
                        else ("模拟诊断无法判断待确认要求" if not evaluated else "模拟诊断未发现明显问题")
                    ),
                    region="画面整体",
                ),
                severity="high" if failed else "low",
                confidence="high",
                possible_causes=["模拟夹具中的固定问题" ] if failed else [],
                violates_confirmed_hard_constraint=(
                    failed and criterion.status == "confirmed" and criterion.importance == "hard"
                ),
            )
        )
    if not criteria:
        items.append(
            DiagnosisItem(
                item_id=f"diag_{candidate.id}_observation",
                kind="observation",
                verdict="uncertain",
                evidence=Evidence(description="没有可验证的创作要求", region="画面整体"),
                severity="low",
                confidence="low",
                possible_causes=["请先确认创作规格"],
            )
        )
    return DiagnosisResult.model_validate_json(json.dumps({
        "summary": "模拟诊断：存在一项待修复问题" if any(item.verdict == "fail" for item in items) else "模拟诊断：当前要求均通过",
        "items": [item.model_dump(mode="json") for item in items],
        "observations": [],
        "uncertainties": [] if criteria else ["当前规格没有可验证要求"],
    }, ensure_ascii=False))


def generate_patch(
    spec: Any,
    reviewed_items: list[DiagnosisItem],
    base_prompt: str | None,
    base_params: dict[str, Any],
) -> PatchResult:
    changes = [
        PromptChange(
            operation="add",
            from_value=None,
            to=f"修复：{item.evidence.description}",
            reason="对应用户选中的诊断问题",
            diagnosis_item_ids=[item.item_id],
        )
        for item in reviewed_items
    ]
    additions = [change.to for change in changes if change.to]
    merged_prompt = base_prompt
    if additions:
        merged_prompt = "\n".join([part for part in [base_prompt, *additions] if part])
    return PatchResult.model_validate_json(json.dumps({
        "prompt_changes": [change.model_dump(mode="json", by_alias=True) for change in changes],
        "parameter_changes": [],
        "keep_unchanged": [
            criterion.statement
            for criterion in spec.criteria
            if criterion.criterion_id not in {item.criterion_id for item in reviewed_items}
        ],
        "conflicts": [],
        "side_effects": [],
        "merged_prompt": merged_prompt,
        "merged_params": dict(base_params),
        "base_prompt_missing": not bool(base_prompt),
    }, ensure_ascii=False))
