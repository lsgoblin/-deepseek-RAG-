"""Small SQLite persistence layer for the local single-user demo."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


SCHEMA_VERSION = 1


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def json_loads(value: str | None, default: Any = None) -> Any:
    return default if value is None else json.loads(value)


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        # 文件移动和数据库写入由业务服务协调；数据库部分始终使用显式事务。
        connection = self.connect()
        try:
            connection.execute("BEGIN")
            yield connection
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                PRAGMA user_version = 1;

                -- parent_task_id 使用 RESTRICT，保证父任务不能绕过子分支直接删除。
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    parent_task_id TEXT REFERENCES tasks(id) ON DELETE RESTRICT,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT NOT NULL CHECK (status IN ('draft', 'active', 'accepted')),
                    current_spec_version_id TEXT,
                    accepted_candidate_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS spec_versions (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    version_no INTEGER NOT NULL CHECK (version_no > 0),
                    status TEXT NOT NULL CHECK (status IN ('draft', 'confirmed')),
                    source_version_id TEXT REFERENCES spec_versions(id) ON DELETE SET NULL,
                    spec_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    confirmed_at TEXT,
                    UNIQUE(task_id, version_no)
                );

                CREATE TABLE IF NOT EXISTS generation_rounds (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    round_no INTEGER NOT NULL CHECK (round_no > 0),
                    spec_version_id TEXT NOT NULL REFERENCES spec_versions(id) ON DELETE CASCADE,
                    platform TEXT,
                    model_name TEXT,
                    prompt_snapshot TEXT,
                    params_json TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('waiting_images', 'diagnosing', 'awaiting_review', 'patch_ready', 'closed')),
                    created_at TEXT NOT NULL,
                    UNIQUE(task_id, round_no)
                );

                CREATE TABLE IF NOT EXISTS submissions (
                    id TEXT PRIMARY KEY,
                    round_id TEXT NOT NULL REFERENCES generation_rounds(id) ON DELETE CASCADE,
                    note TEXT,
                    submitted_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS candidates (
                    id TEXT PRIMARY KEY,
                    round_id TEXT NOT NULL REFERENCES generation_rounds(id) ON DELETE CASCADE,
                    submission_id TEXT NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
                    original_path TEXT NOT NULL,
                    sanitized_path TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    width INTEGER NOT NULL,
                    height INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(round_id, sha256)
                );

                CREATE TABLE IF NOT EXISTS diagnoses (
                    id TEXT PRIMARY KEY,
                    candidate_id TEXT NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
                    spec_version_id TEXT NOT NULL REFERENCES spec_versions(id) ON DELETE CASCADE,
                    status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'succeeded', 'failed_retryable', 'failed_final')),
                    prompt_version TEXT,
                    result_json TEXT,
                    error_json TEXT,
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                );

                CREATE TABLE IF NOT EXISTS diagnosis_reviews (
                    id TEXT PRIMARY KEY,
                    diagnosis_id TEXT NOT NULL REFERENCES diagnoses(id) ON DELETE CASCADE,
                    item_id TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    corrected_json TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS patches (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    source_round_id TEXT NOT NULL REFERENCES generation_rounds(id) ON DELETE CASCADE,
                    source_spec_version_id TEXT NOT NULL REFERENCES spec_versions(id) ON DELETE CASCADE,
                    selected_item_ids_json TEXT NOT NULL,
                    base_prompt TEXT,
                    base_params_json TEXT NOT NULL,
                    diff_json TEXT NOT NULL,
                    merged_prompt TEXT,
                    merged_params_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS consents (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    provider TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    purpose TEXT NOT NULL,
                    data_types_json TEXT NOT NULL,
                    policy_version TEXT NOT NULL,
                    scope_hash TEXT NOT NULL,
                    granted_at TEXT NOT NULL,
                    revoked_at TEXT
                );

                CREATE TABLE IF NOT EXISTS model_calls (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    diagnosis_id TEXT REFERENCES diagnoses(id) ON DELETE SET NULL,
                    provider TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    prompt_version TEXT,
                    request_hash TEXT NOT NULL,
                    image_hashes_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempt_no INTEGER NOT NULL,
                    latency_ms INTEGER,
                    usage_json TEXT,
                    error_code TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS audit_events (
                    id TEXT PRIMARY KEY,
                    task_id TEXT,
                    event_type TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT,
                    details_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS idempotency_keys (
                    key TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (key, operation)
                );

                CREATE TABLE IF NOT EXISTS deletion_jobs (
                    id TEXT PRIMARY KEY,
                    deleted_task_id TEXT NOT NULL,
                    paths_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_json TEXT,
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_spec_versions_task ON spec_versions(task_id, version_no);
                CREATE INDEX IF NOT EXISTS idx_rounds_task ON generation_rounds(task_id, round_no);
                CREATE INDEX IF NOT EXISTS idx_candidates_hash ON candidates(sha256);
                CREATE INDEX IF NOT EXISTS idx_diagnoses_candidate ON diagnoses(candidate_id);
                CREATE INDEX IF NOT EXISTS idx_audit_task ON audit_events(task_id, created_at);

                -- confirmed 规格只允许从 draft 转入，不允许再改内容或状态。
                CREATE TRIGGER IF NOT EXISTS prevent_confirmed_spec_mutation
                BEFORE UPDATE ON spec_versions
                WHEN OLD.status = 'confirmed' AND (NEW.status <> OLD.status OR NEW.spec_json <> OLD.spec_json)
                BEGIN
                    SELECT RAISE(ABORT, 'confirmed spec versions are immutable');
                END;
                """
            )
            connection.execute(
                "UPDATE diagnoses SET status = 'failed_retryable', error_json = ?, completed_at = ? "
                "WHERE status IN ('queued', 'running')",
                (json_dumps({"code": "FAILED_INTERRUPTED", "message": "process restarted"}), utc_now()),
            )

    def fetchone(self, query: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        with self.connect() as connection:
            return connection.execute(query, params).fetchone()

    def fetchall(self, query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return list(connection.execute(query, params).fetchall())

    def audit(self, connection: sqlite3.Connection, task_id: str | None, event_type: str, entity_type: str, entity_id: str | None, details: Any = None) -> None:
        import uuid

        connection.execute(
            "INSERT INTO audit_events(id, task_id, event_type, entity_type, entity_id, details_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), task_id, event_type, entity_type, entity_id, json_dumps(details or {}), utc_now()),
        )
