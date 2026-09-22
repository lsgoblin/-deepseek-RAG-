"""Application services and domain rules for the local mock-AI workflow."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from .ai_gateway import (
    DIAGNOSIS_PROMPT_VERSION,
    DiagnosisItem,
    DiagnosisResult,
    diagnose_candidate,
    extract_spec,
    generate_patch,
)
from .iteracanvas_config import Settings
from .iteracanvas_db import Database, json_dumps, json_loads, utc_now
from .iteracanvas_files import (
    ImageValidationError,
    ValidatedImage,
    move_task_to_trash,
    remove_paths,
    remove_trash,
    store_image,
    task_storage_bytes,
    validate_image,
)
from .iteracanvas_models import (
    BranchCreate,
    ComparisonItem,
    ComparisonOut,
    CandidateOut,
    DiagnosisOut,
    DiagnosisReviewOut,
    DiagnosisReviewCreate,
    DeletionReport,
    EffectiveDiagnosisItem,
    PatchCreate,
    PatchOut,
    RoundCreate,
    RoundOut,
    SpecSnapshot,
    SpecVersionCreate,
    SpecVersionOut,
    SubmissionOut,
    TaskCreate,
    TaskDetail,
    TaskSummary,
)


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}


def _not_found(entity: str, entity_id: str) -> AppError:
    return AppError(404, "ENTITY_NOT_FOUND", f"{entity}不存在", {"id": entity_id})


def _task_row(db: Database, task_id: str) -> sqlite3.Row:
    row = db.fetchone("SELECT * FROM tasks WHERE id = ?", (task_id,))
    if row is None:
        raise _not_found("任务", task_id)
    return row


def _task_summary(row: sqlite3.Row) -> TaskSummary:
    return TaskSummary(**dict(row))


def _spec_out(row: sqlite3.Row) -> SpecVersionOut:
    return SpecVersionOut(
        id=row["id"], task_id=row["task_id"], version_no=row["version_no"], status=row["status"],
        source_version_id=row["source_version_id"], spec=SpecSnapshot.model_validate(json_loads(row["spec_json"])),
        created_at=row["created_at"], confirmed_at=row["confirmed_at"],
    )


def _candidate_out(row: sqlite3.Row, cross_round_duplicate: bool = False) -> CandidateOut:
    return CandidateOut(
        id=row["id"], round_id=row["round_id"], submission_id=row["submission_id"], sha256=row["sha256"],
        mime_type=row["mime_type"], width=row["width"], height=row["height"],
        original_path=row["original_path"], sanitized_path=row["sanitized_path"],
        created_at=row["created_at"], cross_round_duplicate=cross_round_duplicate,
    )


def _round_out(db: Database, row: sqlite3.Row) -> RoundOut:
    candidates = db.fetchall("SELECT * FROM candidates WHERE round_id = ? ORDER BY created_at", (row["id"],))
    return RoundOut(
        id=row["id"], task_id=row["task_id"], round_no=row["round_no"], spec_version_id=row["spec_version_id"],
        platform=row["platform"], model_name=row["model_name"], prompt_snapshot=row["prompt_snapshot"],
        params=json_loads(row["params_json"], {}), status=row["status"], created_at=row["created_at"],
        candidates=[_candidate_out(candidate) for candidate in candidates],
    )


def create_task(db: Database, request: TaskCreate) -> TaskSummary:
    now = utc_now()
    task_id = str(uuid4())
    with db.transaction() as connection:
        connection.execute(
            "INSERT INTO tasks(id, title, description, status, created_at, updated_at) VALUES (?, ?, ?, 'draft', ?, ?)",
            (task_id, request.title, request.description, now, now),
        )
        db.audit(connection, task_id, "task.created", "task", task_id)
    return _task_summary(_task_row(db, task_id))


def list_tasks(db: Database) -> list[TaskSummary]:
    return [_task_summary(row) for row in db.fetchall("SELECT * FROM tasks ORDER BY updated_at DESC")]


def get_task(db: Database, task_id: str) -> TaskDetail:
    task = _task_row(db, task_id)
    specs = db.fetchall("SELECT * FROM spec_versions WHERE task_id = ? ORDER BY version_no", (task_id,))
    rounds = db.fetchall("SELECT * FROM generation_rounds WHERE task_id = ? ORDER BY round_no", (task_id,))
    children = db.fetchall("SELECT id FROM tasks WHERE parent_task_id = ? ORDER BY created_at", (task_id,))
    return TaskDetail(
        **dict(task),
        spec_versions=[_spec_out(row) for row in specs],
        rounds=[_round_out(db, row) for row in rounds],
        child_task_ids=[row["id"] for row in children],
    )


def extract_task_spec(db: Database, task_id: str, task_text: str | None, reference_images: list[dict[str, Any]]):
    task = _task_row(db, task_id)
    return extract_spec(task_text if task_text is not None else (task["description"] or ""), reference_images)


def save_spec(db: Database, task_id: str, request: SpecVersionCreate) -> SpecVersionOut:
    # 每次保存都新建版本，不能覆盖历史规格；确认后的版本由数据库触发器保护。
    task = _task_row(db, task_id)
    if task["status"] == "accepted":
        raise AppError(400, "INVALID_STATE_TRANSITION", "已接受任务不可修改规格")
    previous = db.fetchone("SELECT * FROM spec_versions WHERE task_id = ? ORDER BY version_no DESC LIMIT 1", (task_id,))
    version_no = (previous["version_no"] if previous else 0) + 1
    version_id = str(uuid4())
    now = utc_now()
    source_id = task["current_spec_version_id"] or (previous["id"] if previous else None)
    with db.transaction() as connection:
        connection.execute(
            "INSERT INTO spec_versions(id, task_id, version_no, status, source_version_id, spec_json, created_at) VALUES (?, ?, ?, 'draft', ?, ?, ?)",
            (version_id, task_id, version_no, source_id, json_dumps(request.spec.model_dump(mode="json")), now),
        )
        connection.execute("UPDATE tasks SET current_spec_version_id = ?, updated_at = ? WHERE id = ?", (version_id, now, task_id))
        db.audit(connection, task_id, "spec.saved", "spec_version", version_id, {"version_no": version_no})
    return _spec_out(db.fetchone("SELECT * FROM spec_versions WHERE id = ?", (version_id,)))


def confirm_spec(db: Database, version_id: str) -> SpecVersionOut:
    row = db.fetchone("SELECT * FROM spec_versions WHERE id = ?", (version_id,))
    if row is None:
        raise _not_found("规格版本", version_id)
    if row["status"] == "confirmed":
        return _spec_out(row)
    task = _task_row(db, row["task_id"])
    if task["status"] == "accepted":
        raise AppError(400, "INVALID_STATE_TRANSITION", "已接受任务不可确认新规格")
    now = utc_now()
    with db.transaction() as connection:
        connection.execute("UPDATE spec_versions SET status = 'confirmed', confirmed_at = ? WHERE id = ?", (now, version_id))
        connection.execute("UPDATE tasks SET status = 'active', current_spec_version_id = ?, updated_at = ? WHERE id = ?", (version_id, now, task["id"]))
        db.audit(connection, task["id"], "spec.confirmed", "spec_version", version_id)
    return _spec_out(db.fetchone("SELECT * FROM spec_versions WHERE id = ?", (version_id,)))


def create_round(db: Database, task_id: str, request: RoundCreate) -> RoundOut:
    task = _task_row(db, task_id)
    if task["status"] == "accepted":
        raise AppError(400, "INVALID_STATE_TRANSITION", "已接受任务不可创建新轮次")
    spec = db.fetchone("SELECT * FROM spec_versions WHERE id = ? AND task_id = ?", (request.spec_version_id, task_id))
    if spec is None:
        raise _not_found("规格版本", request.spec_version_id)
    if spec["status"] != "confirmed":
        raise AppError(400, "INVALID_STATE_TRANSITION", "生成轮次只能绑定已确认规格")
    last = db.fetchone("SELECT MAX(round_no) AS round_no FROM generation_rounds WHERE task_id = ?", (task_id,))
    round_no = (last["round_no"] or 0) + 1
    round_id = str(uuid4())
    now = utc_now()
    try:
        with db.transaction() as connection:
            connection.execute(
                "INSERT INTO generation_rounds(id, task_id, round_no, spec_version_id, platform, model_name, prompt_snapshot, params_json, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'waiting_images', ?)",
                (round_id, task_id, round_no, request.spec_version_id, request.platform, request.model_name, request.prompt_snapshot, json_dumps(request.params), now),
            )
            connection.execute("UPDATE tasks SET updated_at = ? WHERE id = ?", (now, task_id))
            db.audit(connection, task_id, "round.created", "generation_round", round_id, {"round_no": round_no})
    except sqlite3.IntegrityError as exc:
        raise AppError(409, "ROUND_CONFLICT", "生成轮次创建冲突，请重试") from exc
    return _round_out(db, db.fetchone("SELECT * FROM generation_rounds WHERE id = ?", (round_id,)))


def upload_submission(
    db: Database,
    settings: Settings,
    round_id: str,
    files: list[tuple[str | None, bytes]],
    note: str | None,
) -> SubmissionOut:
    round_row = db.fetchone(
        "SELECT r.*, t.status AS task_status FROM generation_rounds r JOIN tasks t ON t.id = r.task_id WHERE r.id = ?",
        (round_id,),
    )
    if round_row is None:
        raise _not_found("生成轮次", round_id)
    if round_row["task_status"] == "accepted" or round_row["status"] == "closed":
        raise AppError(400, "INVALID_STATE_TRANSITION", "当前轮次不可继续上传")
    if not files:
        raise AppError(400, "INVALID_IMAGE", "至少上传一张图片")

    existing_round_count = db.fetchone("SELECT COUNT(*) AS count FROM candidates WHERE round_id = ?", (round_id,))["count"]
    if existing_round_count + len(files) > settings.max_images_per_round:
        raise AppError(413, "UPLOAD_LIMIT_EXCEEDED", "超过单轮图片数量限制", {"max": settings.max_images_per_round})
    task_count = db.fetchone(
        "SELECT COUNT(*) AS count FROM candidates c JOIN generation_rounds r ON r.id = c.round_id WHERE r.task_id = ?",
        (round_row["task_id"],),
    )["count"]
    if task_count + len(files) > settings.max_images_per_task:
        raise AppError(413, "UPLOAD_LIMIT_EXCEEDED", "超过任务图片数量限制", {"max": settings.max_images_per_task})

    validated: list[ValidatedImage] = []
    seen: set[str] = set()
    for _, content in files:
        try:
            item = validate_image(content, settings)
        except ImageValidationError as exc:
            raise AppError(400, "INVALID_IMAGE", str(exc)) from exc
        if item.sha256 in seen:
            raise AppError(409, "DUPLICATE_CANDIDATE", "同一提交中包含重复图片", {"sha256": item.sha256})
        seen.add(item.sha256)
        existing = db.fetchone("SELECT id FROM candidates WHERE round_id = ? AND sha256 = ?", (round_id, item.sha256))
        if existing:
            # 同轮重复不创建候选图；跨轮重复在下面只作为提示放行。
            raise AppError(409, "DUPLICATE_CANDIDATE", "同一轮次已存在相同图片", {"sha256": item.sha256, "candidate_id": existing["id"]})
        validated.append(item)

    estimated_bytes = sum(len(item.content) * 2 for item in validated)
    if task_storage_bytes(settings, round_row["task_id"]) + estimated_bytes > settings.task_storage_limit_bytes:
        raise AppError(413, "UPLOAD_LIMIT_EXCEEDED", "超过任务本地存储限制", {"max_bytes": settings.task_storage_limit_bytes})

    cross_round = {
        item.sha256
        for item in validated
        if db.fetchone(
            "SELECT 1 FROM candidates c JOIN generation_rounds r ON r.id = c.round_id WHERE r.task_id = ? AND c.round_id <> ? AND c.sha256 = ? LIMIT 1",
            (round_row["task_id"], round_id, item.sha256),
        )
    }
    submission_id = str(uuid4())
    created_at = utc_now()
    stored = []
    try:
        with db.transaction() as connection:
            connection.execute(
                "INSERT INTO submissions(id, round_id, note, submitted_at) VALUES (?, ?, ?, ?)",
                (submission_id, round_id, note, created_at),
            )
            for item in validated:
                candidate_id = str(uuid4())
                stored_image = store_image(settings, round_row["task_id"], round_id, candidate_id, item)
                stored.append(stored_image)
                if task_storage_bytes(settings, round_row["task_id"]) > settings.task_storage_limit_bytes:
                    raise AppError(413, "UPLOAD_LIMIT_EXCEEDED", "超过任务本地存储限制", {"max_bytes": settings.task_storage_limit_bytes})
                connection.execute(
                    "INSERT INTO candidates(id, round_id, submission_id, original_path, sanitized_path, sha256, mime_type, width, height, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (candidate_id, round_id, submission_id, stored_image.original_path, stored_image.sanitized_path, item.sha256, item.mime_type, item.width, item.height, created_at),
                )
            connection.execute("UPDATE tasks SET updated_at = ? WHERE id = ?", (created_at, round_row["task_id"]))
            db.audit(connection, round_row["task_id"], "submission.created", "submission", submission_id, {"candidate_count": len(stored)})
    except Exception:
        for image in stored:
            remove_paths(image.created_paths)
        raise

    candidates = db.fetchall("SELECT * FROM candidates WHERE submission_id = ? ORDER BY created_at", (submission_id,))
    return SubmissionOut(
        id=submission_id, round_id=round_id, note=note, submitted_at=created_at,
        candidates=[_candidate_out(row, row["sha256"] in cross_round) for row in candidates],
    )


def create_branch(db: Database, parent_task_id: str, request: BranchCreate) -> TaskSummary:
    parent = _task_row(db, parent_task_id)
    source = db.fetchone(
        "SELECT * FROM spec_versions WHERE task_id = ? AND status = 'confirmed' ORDER BY version_no DESC LIMIT 1",
        (parent_task_id,),
    )
    if source is None:
        raise AppError(400, "INVALID_STATE_TRANSITION", "没有可继承的已确认规格")
    child_id, spec_id, now = str(uuid4()), str(uuid4()), utc_now()
    title = request.title or f"{parent['title']}（分支）"
    with db.transaction() as connection:
        connection.execute(
            "INSERT INTO tasks(id, parent_task_id, title, description, status, current_spec_version_id, created_at, updated_at) VALUES (?, ?, ?, ?, 'active', ?, ?, ?)",
            (child_id, parent_task_id, title, parent["description"], spec_id, now, now),
        )
        connection.execute(
            "INSERT INTO spec_versions(id, task_id, version_no, status, source_version_id, spec_json, created_at, confirmed_at) VALUES (?, ?, 1, 'confirmed', ?, ?, ?, ?)",
            (spec_id, child_id, source["id"], source["spec_json"], now, now),
        )
        db.audit(connection, child_id, "task.branched", "task", child_id, {"parent_task_id": parent_task_id, "source_spec_version_id": source["id"]})
    return _task_summary(_task_row(db, child_id))


def delete_task(db: Database, settings: Settings, task_id: str) -> DeletionReport:
    task = _task_row(db, task_id)
    children = db.fetchall("SELECT id FROM tasks WHERE parent_task_id = ?", (task_id,))
    if children:
        raise AppError(409, "CHILD_TASKS_EXIST", "父任务存在子分支，必须先删除叶子分支", {"blocking_task_ids": [row["id"] for row in children]})

    job_id = str(uuid4())
    now = utc_now()
    with db.transaction() as connection:
        connection.execute(
            "INSERT INTO deletion_jobs(id, deleted_task_id, paths_json, status, created_at) VALUES (?, ?, ?, 'pending', ?)",
            (job_id, task_id, json_dumps({"task": f"tasks/{task_id}"}), now),
        )
    # 先把文件目录移入隔离区，再删除数据库记录，失败时可以移回原位。
    _, trash_path = move_task_to_trash(settings, task_id, job_id)
    try:
        with db.transaction() as connection:
            connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            connection.execute("UPDATE deletion_jobs SET status = 'database_deleted' WHERE id = ?", (job_id,))
    except Exception as exc:
        if trash_path and trash_path.exists():
            source = settings.tasks_dir / task_id
            source.parent.mkdir(parents=True, exist_ok=True)
            trash_path.rename(source)
        with db.transaction() as connection:
            connection.execute("UPDATE deletion_jobs SET status = 'failed', error_json = ? WHERE id = ?", (json_dumps({"message": str(exc)}), job_id))
        raise AppError(500, "DELETE_FAILED", "删除任务失败") from exc

    try:
        remove_trash(settings, trash_path)
        with db.transaction() as connection:
            connection.execute("UPDATE deletion_jobs SET status = 'completed', completed_at = ? WHERE id = ?", (utc_now(), job_id))
    except Exception as exc:
        with db.transaction() as connection:
            connection.execute("UPDATE deletion_jobs SET status = 'partial', error_json = ? WHERE id = ?", (json_dumps({"message": str(exc)}), job_id))
        return DeletionReport(task_id=task_id, deletion_job_id=job_id, status="partial", database_deleted=True, files_deleted=False)
    return DeletionReport(task_id=task_id, deletion_job_id=job_id, status="completed", database_deleted=True, files_deleted=True)


def request_hash(payload: Any) -> str:
    return hashlib.sha256(json_dumps(payload).encode("utf-8")).hexdigest()


def replay_idempotency(db: Database, key: str | None, operation: str, body_hash: str) -> dict[str, Any] | None:
    if not key:
        return None
    row = db.fetchone("SELECT request_hash, response_json FROM idempotency_keys WHERE key = ? AND operation = ?", (key, operation))
    if row is None:
        return None
    if row["request_hash"] != body_hash:
        raise AppError(409, "IDEMPOTENCY_CONFLICT", "幂等键已用于不同请求")
    return json.loads(row["response_json"])


def save_idempotency(db: Database, key: str | None, operation: str, body_hash: str, response: Any) -> None:
    if not key:
        return
    try:
        with db.transaction() as connection:
            connection.execute(
                "INSERT INTO idempotency_keys(key, operation, request_hash, response_json, created_at) VALUES (?, ?, ?, ?, ?)",
                (key, operation, body_hash, json_dumps(response), utc_now()),
            )
    except sqlite3.IntegrityError as exc:
        raise AppError(409, "IDEMPOTENCY_CONFLICT", "幂等键已被并发请求占用") from exc


def _diagnosis_row(db: Database, diagnosis_id: str) -> sqlite3.Row:
    row = db.fetchone("SELECT * FROM diagnoses WHERE id = ?", (diagnosis_id,))
    if row is None:
        raise _not_found("诊断", diagnosis_id)
    return row


def _diagnosis_items(row: sqlite3.Row) -> list[DiagnosisItem]:
    if not row["result_json"]:
        return []
    result = DiagnosisResult.model_validate(json_loads(row["result_json"]))
    return [*result.items, *result.observations]


def _review_rows(db: Database, diagnosis_id: str) -> list[sqlite3.Row]:
    return db.fetchall(
        "SELECT * FROM diagnosis_reviews WHERE diagnosis_id = ? ORDER BY created_at, id",
        (diagnosis_id,),
    )


def _effective_diagnosis_items(db: Database, row: sqlite3.Row) -> list[EffectiveDiagnosisItem]:
    raw_items = {item.item_id: item for item in _diagnosis_items(row)}
    stacks: dict[str, list[tuple[DiagnosisItem, str]]] = {item_id: [] for item_id in raw_items}
    for review in _review_rows(db, row["id"]):
        item_id = review["item_id"]
        if item_id not in raw_items:
            continue
        if review["decision"] == "revert":
            if stacks[item_id]:
                stacks[item_id].pop()
            continue
        original = raw_items[item_id]
        if review["decision"] == "confirm":
            item, resolution = original, "confirmed"
        elif review["decision"] == "correct":
            corrected = DiagnosisItem.model_validate(json_loads(review["corrected_json"]))
            item, resolution = corrected, "corrected"
        elif review["decision"] == "not_applicable":
            item = original.model_copy(update={"verdict": "not_applicable", "violates_confirmed_hard_constraint": False})
            resolution = "not_applicable"
        else:
            item = original.model_copy(update={"verdict": "uncertain", "violates_confirmed_hard_constraint": False})
            resolution = "cannot_judge"
        stacks[item_id].append((item, resolution))

    effective: list[EffectiveDiagnosisItem] = []
    for item_id, original in raw_items.items():
        item, resolution = stacks[item_id][-1] if stacks[item_id] else (original, "unreviewed")
        effective.append(
            EffectiveDiagnosisItem(
                **item.model_dump(mode="json"),
                resolution=resolution,
            )
        )
    return effective


def _diagnosis_out(db: Database, row: sqlite3.Row) -> DiagnosisOut:
    return DiagnosisOut(
        id=row["id"],
        candidate_id=row["candidate_id"],
        spec_version_id=row["spec_version_id"],
        status=row["status"],
        prompt_version=row["prompt_version"],
        result=json_loads(row["result_json"]),
        error=json_loads(row["error_json"]),
        created_at=row["created_at"],
        completed_at=row["completed_at"],
        reviews=[
            DiagnosisReviewOut(
                id=review["id"], diagnosis_id=review["diagnosis_id"], item_id=review["item_id"],
                decision=review["decision"], corrected=json_loads(review["corrected_json"]),
                created_at=review["created_at"],
            )
            for review in _review_rows(db, row["id"])
        ],
        effective_items=_effective_diagnosis_items(db, row) if row["status"] == "succeeded" else [],
    )


def get_diagnosis(db: Database, diagnosis_id: str) -> DiagnosisOut:
    return _diagnosis_out(db, _diagnosis_row(db, diagnosis_id))


def get_effective_diagnosis_items(db: Database, diagnosis_id: str) -> list[EffectiveDiagnosisItem]:
    row = _diagnosis_row(db, diagnosis_id)
    if row["status"] != "succeeded":
        return []
    return _effective_diagnosis_items(db, row)


def start_diagnosis(db: Database, candidate_id: str) -> DiagnosisOut:
    row = db.fetchone(
        """
        SELECT c.id AS candidate_id, c.sha256, r.id AS round_id, r.round_no, r.status AS round_status,
               r.task_id, r.spec_version_id, t.status AS task_status
        FROM candidates c
        JOIN generation_rounds r ON r.id = c.round_id
        JOIN tasks t ON t.id = r.task_id
        WHERE c.id = ?
        """,
        (candidate_id,),
    )
    if row is None:
        raise _not_found("候选图", candidate_id)
    if row["task_status"] == "accepted" or row["round_status"] == "closed":
        raise AppError(400, "INVALID_STATE_TRANSITION", "当前候选图不可诊断")
    existing = db.fetchone(
        "SELECT * FROM diagnoses WHERE candidate_id = ? ORDER BY created_at DESC LIMIT 1",
        (candidate_id,),
    )
    if existing is not None:
        if existing["status"] in {"queued", "running", "succeeded"}:
            raise AppError(409, "DIAGNOSIS_EXISTS", "候选图已有可用诊断", {"diagnosis_id": existing["id"]})
        now = utc_now()
        with db.transaction() as connection:
            connection.execute(
                "UPDATE diagnoses SET status = 'queued', result_json = NULL, error_json = NULL, completed_at = NULL WHERE id = ?",
                (existing["id"],),
            )
            connection.execute("UPDATE generation_rounds SET status = 'diagnosing' WHERE id = ?", (row["round_id"],))
            db.audit(connection, row["task_id"], "diagnosis.retried", "diagnosis", existing["id"], {"candidate_id": candidate_id})
        return _diagnosis_out(db, _diagnosis_row(db, existing["id"]))

    diagnosis_id, now = str(uuid4()), utc_now()
    with db.transaction() as connection:
        connection.execute(
            "INSERT INTO diagnoses(id, candidate_id, spec_version_id, status, prompt_version, created_at) VALUES (?, ?, ?, 'queued', ?, ?)",
            (diagnosis_id, candidate_id, row["spec_version_id"], DIAGNOSIS_PROMPT_VERSION, now),
        )
        connection.execute(
            "UPDATE generation_rounds SET status = 'diagnosing' WHERE id = ?",
            (row["round_id"],),
        )
        connection.execute("UPDATE tasks SET updated_at = ? WHERE id = ?", (now, row["task_id"]))
        db.audit(connection, row["task_id"], "diagnosis.queued", "diagnosis", diagnosis_id, {"candidate_id": candidate_id})
    return _diagnosis_out(db, _diagnosis_row(db, diagnosis_id))


def run_diagnosis(db: Database, diagnosis_id: str, mode: str = "mock") -> None:
    diagnosis = _diagnosis_row(db, diagnosis_id)
    context = db.fetchone(
        """
        SELECT d.*, c.id AS candidate_id, c.sha256, r.id AS round_id, r.round_no, r.task_id,
               r.status AS round_status, r.prompt_snapshot, r.params_json,
               s.spec_json, t.status AS task_status
        FROM diagnoses d
        JOIN candidates c ON c.id = d.candidate_id
        JOIN generation_rounds r ON r.id = c.round_id
        JOIN spec_versions s ON s.id = d.spec_version_id
        JOIN tasks t ON t.id = r.task_id
        WHERE d.id = ?
        """,
        (diagnosis_id,),
    )
    if context is None or context["status"] not in {"queued", "running"}:
        return
    now = utc_now()
    call_id = str(uuid4())
    with db.transaction() as connection:
        connection.execute("UPDATE diagnoses SET status = 'running' WHERE id = ?", (diagnosis_id,))
        connection.execute(
            "INSERT INTO model_calls(id, task_id, diagnosis_id, provider, model_name, prompt_version, request_hash, image_hashes_json, status, attempt_no, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'running', 1, ?)",
            (
                call_id,
                context["task_id"],
                diagnosis_id,
                mode,
                "mock-ai",
                DIAGNOSIS_PROMPT_VERSION,
                request_hash({"diagnosis_id": diagnosis_id, "sha256": context["sha256"]}),
                json_dumps([context["sha256"]]),
                now,
            ),
        )

    try:
        if mode != "mock":
            raise ValueError(f"AI_MODE={mode} 暂未实现真实供应商")
        from .iteracanvas_models import SpecSnapshot

        spec = SpecSnapshot.model_validate(json_loads(context["spec_json"]))
        result = diagnose_candidate(
            spec,
            SimpleNamespace(id=context["candidate_id"]),
            generation_context={"round_no": context["round_no"]},
        )
        criterion_ids = {criterion.criterion_id for criterion in spec.criteria}
        for item in [*result.items, *result.observations]:
            if item.kind == "criterion" and item.criterion_id not in criterion_ids:
                raise ValueError(f"unknown criterion_id: {item.criterion_id}")
        completed = utc_now()
        payload = result.model_dump(mode="json", by_alias=True)
        with db.transaction() as connection:
            connection.execute(
                "UPDATE diagnoses SET status = 'succeeded', result_json = ?, completed_at = ? WHERE id = ?",
                (json_dumps(payload), completed, diagnosis_id),
            )
            connection.execute(
                "UPDATE generation_rounds SET status = 'awaiting_review' WHERE id = ?",
                (context["round_id"],),
            )
            connection.execute(
                "UPDATE model_calls SET status = 'succeeded', latency_ms = ?, usage_json = ? WHERE id = ?",
                (0, json_dumps({"mode": "mock"}), call_id),
            )
            db.audit(connection, context["task_id"], "diagnosis.succeeded", "diagnosis", diagnosis_id)
    except Exception as exc:
        error = {"code": "MODEL_OUTPUT_INVALID", "message": str(exc)}
        completed = utc_now()
        with db.transaction() as connection:
            connection.execute(
                "UPDATE diagnoses SET status = 'failed_retryable', error_json = ?, completed_at = ? WHERE id = ?",
                (json_dumps(error), completed, diagnosis_id),
            )
            connection.execute(
                "UPDATE generation_rounds SET status = 'waiting_images' WHERE id = ?",
                (context["round_id"],),
            )
            connection.execute(
                "UPDATE model_calls SET status = 'failed', error_code = ? WHERE id = ?",
                (error["code"], call_id),
            )
            db.audit(connection, context["task_id"], "diagnosis.failed", "diagnosis", diagnosis_id, error)


def add_diagnosis_review(db: Database, diagnosis_id: str, request: DiagnosisReviewCreate) -> DiagnosisReviewOut:
    row = _diagnosis_row(db, diagnosis_id)
    if row["status"] != "succeeded":
        raise AppError(400, "INVALID_STATE_TRANSITION", "诊断尚未成功，不能复核")
    raw = {item.item_id: item for item in _diagnosis_items(row)}
    if request.item_id not in raw:
        raise AppError(400, "INVALID_REVIEW_ITEM", "复核项不属于当前诊断", {"item_id": request.item_id})
    if request.decision == "correct":
        if request.corrected is None:
            raise AppError(400, "INVALID_REVIEW", "correct 决策必须提供 corrected")
        corrected = dict(raw[request.item_id].model_dump(mode="json"))
        corrected.update(request.corrected)
        corrected["item_id"] = request.item_id
        try:
            checked = DiagnosisItem.model_validate(corrected)
        except ValueError as exc:
            raise AppError(422, "INVALID_REVIEW", "纠正后的诊断结构无效", {"error": str(exc)}) from exc
        if checked.criterion_id != raw[request.item_id].criterion_id:
            raise AppError(422, "INVALID_REVIEW", "不能修改诊断项关联的 criterion_id")
        corrected_payload = checked.model_dump(mode="json")
    else:
        corrected_payload = None
    if request.decision == "revert" and not any(review["item_id"] == request.item_id for review in _review_rows(db, diagnosis_id)):
        raise AppError(400, "INVALID_REVIEW", "没有可撤销的复核")

    review_id, now = str(uuid4()), utc_now()
    with db.transaction() as connection:
        connection.execute(
            "INSERT INTO diagnosis_reviews(id, diagnosis_id, item_id, decision, corrected_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (review_id, diagnosis_id, request.item_id, request.decision, json_dumps(corrected_payload) if corrected_payload else None, now),
        )
        candidate = db.fetchone(
            "SELECT r.task_id FROM diagnoses d JOIN candidates c ON c.id = d.candidate_id JOIN generation_rounds r ON r.id = c.round_id WHERE d.id = ?",
            (diagnosis_id,),
        )
        db.audit(connection, candidate["task_id"], "diagnosis.reviewed", "diagnosis_review", review_id, {"decision": request.decision, "item_id": request.item_id})
    return DiagnosisReviewOut(
        id=review_id, diagnosis_id=diagnosis_id, item_id=request.item_id,
        decision=request.decision, corrected=corrected_payload, created_at=now,
    )


def _apply_parameter_changes(base: dict[str, Any], changes: list[dict[str, Any]]) -> dict[str, Any]:
    merged = dict(base)
    for change in changes:
        operation, name = change["operation"], change["name"]
        if operation in {"add", "replace"}:
            merged[name] = change.get("new_value")
        elif operation == "remove":
            merged.pop(name, None)
        elif operation != "keep":
            raise AppError(422, "MODEL_OUTPUT_INVALID", f"不支持的参数操作: {operation}")
    return merged


def create_patch(db: Database, round_id: str, request: PatchCreate) -> PatchOut:
    round_row = db.fetchone("SELECT * FROM generation_rounds WHERE id = ?", (round_id,))
    if round_row is None:
        raise _not_found("生成轮次", round_id)
    if round_row["status"] not in {"awaiting_review", "patch_ready"}:
        raise AppError(400, "INVALID_STATE_TRANSITION", "当前轮次尚未完成诊断复核")
    spec_row = db.fetchone("SELECT * FROM spec_versions WHERE id = ?", (round_row["spec_version_id"],))
    diagnoses = db.fetchall(
        "SELECT d.* FROM diagnoses d JOIN candidates c ON c.id = d.candidate_id WHERE c.round_id = ? AND d.status = 'succeeded' ORDER BY d.created_at",
        (round_id,),
    )
    effective_by_id = {
        item.item_id: item
        for diagnosis in diagnoses
        for item in _effective_diagnosis_items(db, diagnosis)
    }
    selected = []
    for item_id in request.selected_item_ids:
        item = effective_by_id.get(item_id)
        if item is None:
            raise AppError(400, "INVALID_PATCH_ITEM", "补丁项不属于当前轮次", {"item_id": item_id})
        if item.verdict in {"pass", "not_applicable"} or item.resolution in {"not_applicable", "cannot_judge"}:
            raise AppError(400, "INVALID_PATCH_ITEM", "只能选择未通过或不确定的问题", {"item_id": item_id})
        selected.append(DiagnosisItem.model_validate(item.model_dump(exclude={"resolution"})))

    from .iteracanvas_models import SpecSnapshot

    spec = SpecSnapshot.model_validate(json_loads(spec_row["spec_json"]))
    base_params = json_loads(round_row["params_json"], {})
    result = generate_patch(spec, selected, round_row["prompt_snapshot"], base_params)
    result_payload = result.model_dump(mode="json", by_alias=True)
    merged_params = _apply_parameter_changes(base_params, result_payload["parameter_changes"])
    if merged_params != result_payload["merged_params"]:
        raise AppError(422, "MODEL_OUTPUT_INVALID", "模型返回的 merged_params 与服务端计算不一致")
    patch_id, now = str(uuid4()), utc_now()
    with db.transaction() as connection:
        connection.execute(
            "INSERT INTO patches(id, task_id, source_round_id, source_spec_version_id, selected_item_ids_json, base_prompt, base_params_json, diff_json, merged_prompt, merged_params_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                patch_id, round_row["task_id"], round_id, round_row["spec_version_id"],
                json_dumps(request.selected_item_ids), round_row["prompt_snapshot"], json_dumps(base_params),
                json_dumps(result_payload), result_payload["merged_prompt"], json_dumps(merged_params), now,
            ),
        )
        connection.execute("UPDATE generation_rounds SET status = 'patch_ready' WHERE id = ?", (round_id,))
        connection.execute("UPDATE tasks SET updated_at = ? WHERE id = ?", (now, round_row["task_id"]))
        db.audit(connection, round_row["task_id"], "patch.created", "patch", patch_id, {"round_id": round_id, "selected_item_ids": request.selected_item_ids})
    return PatchOut(
        id=patch_id, task_id=round_row["task_id"], source_round_id=round_id,
        source_spec_version_id=round_row["spec_version_id"], selected_item_ids=request.selected_item_ids,
        base_prompt=round_row["prompt_snapshot"], base_params=base_params, result=result_payload, created_at=now,
    )


def compare_round(db: Database, round_id: str) -> ComparisonOut:
    current = db.fetchone("SELECT * FROM generation_rounds WHERE id = ?", (round_id,))
    if current is None:
        raise _not_found("生成轮次", round_id)
    previous = db.fetchone(
        "SELECT * FROM generation_rounds WHERE task_id = ? AND round_no < ? ORDER BY round_no DESC LIMIT 1",
        (current["task_id"], current["round_no"]),
    )
    if previous is None:
        return ComparisonOut(round_id=round_id, previous_round_id=None, items=[])

    def verdicts(round_id_value: str) -> dict[str, str]:
        rows = db.fetchall(
            "SELECT d.* FROM diagnoses d JOIN candidates c ON c.id = d.candidate_id WHERE c.round_id = ? AND d.status = 'succeeded' ORDER BY d.created_at",
            (round_id_value,),
        )
        result: dict[str, str] = {}
        for diagnosis in rows:
            for item in _effective_diagnosis_items(db, diagnosis):
                if item.criterion_id and item.criterion_id not in result:
                    result[item.criterion_id] = item.verdict
        return result

    before, after = verdicts(previous["id"]), verdicts(round_id)
    items: list[ComparisonItem] = []
    for criterion_id in sorted(set(before) & set(after)):
        old, new = before[criterion_id], after[criterion_id]
        if "not_applicable" in {old, new}:
            outcome = "not_compared"
        elif "uncertain" in {old, new}:
            outcome = "uncertain"
        elif old == "fail" and new == "pass":
            outcome = "improved"
        elif old == "pass" and new == "fail":
            outcome = "regressed"
        else:
            outcome = "unchanged"
        items.append(ComparisonItem(criterion_id=criterion_id, previous_verdict=old, current_verdict=new, outcome=outcome))
    return ComparisonOut(round_id=round_id, previous_round_id=previous["id"], items=items)


def accept_candidate(db: Database, task_id: str, candidate_id: str) -> TaskSummary:
    row = db.fetchone(
        """
        SELECT c.id, r.id AS round_id, r.task_id, d.id AS diagnosis_id, d.status AS diagnosis_status
        FROM candidates c JOIN generation_rounds r ON r.id = c.round_id
        LEFT JOIN diagnoses d ON d.candidate_id = c.id
        WHERE c.id = ? AND r.task_id = ? ORDER BY d.created_at DESC LIMIT 1
        """,
        (candidate_id, task_id),
    )
    if row is None:
        raise _not_found("候选图", candidate_id)
    task = _task_row(db, task_id)
    if task["status"] == "accepted":
        if task["accepted_candidate_id"] == candidate_id:
            return _task_summary(task)
        raise AppError(400, "INVALID_STATE_TRANSITION", "已接受任务不可更换候选图")
    if row["diagnosis_status"] != "succeeded":
        raise AppError(400, "INVALID_STATE_TRANSITION", "只能接受已完成诊断的候选图")
    now = utc_now()
    with db.transaction() as connection:
        connection.execute("UPDATE tasks SET status = 'accepted', accepted_candidate_id = ?, updated_at = ? WHERE id = ?", (candidate_id, now, task_id))
        connection.execute("UPDATE generation_rounds SET status = 'closed' WHERE id = ?", (row["round_id"],))
        db.audit(connection, task_id, "task.accepted", "candidate", candidate_id, {"round_id": row["round_id"]})
    return _task_summary(_task_row(db, task_id))
