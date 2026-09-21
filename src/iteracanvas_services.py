"""Phase 1 application services and domain rules."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any
from uuid import uuid4

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
    CandidateOut,
    DeletionReport,
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
