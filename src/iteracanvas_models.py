"""Pydantic models shared by the API and persistence boundary."""

from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Criterion(StrictModel):
    criterion_id: str = Field(default_factory=lambda: f"crt_{uuid4().hex}")
    category: str
    statement: str
    importance: Literal["hard", "soft", "undecided"] = "soft"
    source: Literal["user", "ai_inference", "system"] = "user"
    status: Literal["confirmed", "pending", "unknown", "skipped"] = "confirmed"
    verification_mode: Literal["visual", "prompt", "parameter", "user"] = "visual"


class SpecSnapshot(StrictModel):
    context: dict[str, Any] = Field(default_factory=dict)
    criteria: list[Criterion] = Field(default_factory=list)
    reference_images: list[dict[str, Any]] = Field(default_factory=list)


class TaskCreate(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=20_000)


class BranchCreate(StrictModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)


class SpecVersionCreate(StrictModel):
    spec: SpecSnapshot


class RoundCreate(StrictModel):
    spec_version_id: str
    platform: str | None = Field(default=None, max_length=200)
    model_name: str | None = Field(default=None, max_length=200)
    prompt_snapshot: str | None = Field(default=None, max_length=100_000)
    params: dict[str, Any] = Field(default_factory=dict)


class TaskSummary(BaseModel):
    id: str
    parent_task_id: str | None
    title: str
    description: str | None
    status: str
    current_spec_version_id: str | None
    accepted_candidate_id: str | None
    created_at: str
    updated_at: str


class SpecVersionOut(BaseModel):
    id: str
    task_id: str
    version_no: int
    status: str
    source_version_id: str | None
    spec: SpecSnapshot
    created_at: str
    confirmed_at: str | None


class CandidateOut(BaseModel):
    id: str
    round_id: str
    submission_id: str
    sha256: str
    mime_type: str
    width: int
    height: int
    original_path: str
    sanitized_path: str
    created_at: str
    cross_round_duplicate: bool = False


class SubmissionOut(BaseModel):
    id: str
    round_id: str
    note: str | None
    submitted_at: str
    candidates: list[CandidateOut]


class RoundOut(BaseModel):
    id: str
    task_id: str
    round_no: int
    spec_version_id: str
    platform: str | None
    model_name: str | None
    prompt_snapshot: str | None
    params: dict[str, Any]
    status: str
    created_at: str
    candidates: list[CandidateOut] = Field(default_factory=list)


class TaskDetail(TaskSummary):
    spec_versions: list[SpecVersionOut] = Field(default_factory=list)
    rounds: list[RoundOut] = Field(default_factory=list)
    child_task_ids: list[str] = Field(default_factory=list)


class DeletionReport(BaseModel):
    task_id: str
    deletion_job_id: str
    status: str
    database_deleted: bool
    files_deleted: bool
    third_party_status: str = "not_applicable_local_demo"


class DiagnosisCreate(StrictModel):
    model_name: str | None = Field(default=None, max_length=200)


class DiagnosisReviewCreate(StrictModel):
    item_id: str
    decision: Literal["confirm", "correct", "not_applicable", "cannot_judge", "revert"]
    corrected: dict[str, Any] | None = Field(
        default=None,
        validation_alias=AliasChoices("corrected", "corrected_json", "corrected_item"),
    )


class SpecExtractionCreate(StrictModel):
    task_text: str | None = Field(default=None, max_length=20_000)
    reference_images: list[dict[str, Any]] = Field(default_factory=list)


class PatchCreate(StrictModel):
    selected_item_ids: list[str] = Field(min_length=1)


class AcceptCreate(StrictModel):
    candidate_id: str


class DiagnosisReviewOut(BaseModel):
    id: str
    diagnosis_id: str
    item_id: str
    decision: str
    corrected: dict[str, Any] | None = None
    created_at: str


class EffectiveDiagnosisItem(BaseModel):
    item_id: str
    criterion_id: str | None = None
    kind: str
    verdict: str
    evidence: dict[str, Any]
    severity: str
    confidence: str
    possible_causes: list[str] = Field(default_factory=list)
    violates_confirmed_hard_constraint: bool = False
    resolution: str


class DiagnosisOut(BaseModel):
    id: str
    candidate_id: str
    spec_version_id: str
    status: str
    prompt_version: str | None = None
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    created_at: str
    completed_at: str | None = None
    reviews: list[DiagnosisReviewOut] = Field(default_factory=list)
    effective_items: list[EffectiveDiagnosisItem] = Field(default_factory=list)


class PatchOut(BaseModel):
    id: str
    task_id: str
    source_round_id: str
    source_spec_version_id: str
    selected_item_ids: list[str]
    base_prompt: str | None
    base_params: dict[str, Any]
    result: dict[str, Any]
    created_at: str


class ComparisonItem(BaseModel):
    criterion_id: str
    previous_verdict: str | None = None
    current_verdict: str | None = None
    outcome: Literal["improved", "regressed", "unchanged", "uncertain", "not_compared"]


class ComparisonOut(BaseModel):
    round_id: str
    previous_round_id: str | None
    items: list[ComparisonItem] = Field(default_factory=list)
