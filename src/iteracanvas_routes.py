"""FastAPI routes for the phase 1 persistence skeleton."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, Header, Request, UploadFile
from fastapi.responses import JSONResponse

from .iteracanvas_models import BranchCreate, RoundCreate, SpecVersionCreate, TaskCreate
from .iteracanvas_services import (
    AppError,
    confirm_spec,
    create_branch,
    create_round,
    create_task,
    delete_task,
    get_task,
    list_tasks,
    replay_idempotency,
    request_hash,
    save_idempotency,
    save_spec,
    upload_submission,
)


router = APIRouter(prefix="/api/v1")


def _db(request: Request):
    return request.app.state.db


def _settings(request: Request):
    return request.app.state.settings


def _response(data, status_code: int = 200) -> JSONResponse:
    return JSONResponse(data.model_dump(mode="json") if hasattr(data, "model_dump") else data, status_code=status_code)


@router.post("/tasks", status_code=201)
def post_task(request: Request, body: TaskCreate, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    # POST 重放直接返回第一次结果，避免双击产生重复任务。
    body_hash = request_hash(body.model_dump(mode="json"))
    replay = replay_idempotency(_db(request), idempotency_key, "create_task", body_hash)
    if replay is not None:
        return _response(replay, 201)
    result = create_task(_db(request), body)
    data = result.model_dump(mode="json")
    save_idempotency(_db(request), idempotency_key, "create_task", body_hash, data)
    return _response(data, 201)


@router.get("/tasks")
def get_tasks(request: Request):
    return {"items": [item.model_dump(mode="json") for item in list_tasks(_db(request))]}


@router.get("/tasks/{task_id}")
def get_task_by_id(request: Request, task_id: str):
    return _response(get_task(_db(request), task_id))


@router.post("/tasks/{task_id}/spec-versions", status_code=201)
def post_spec(request: Request, task_id: str, body: SpecVersionCreate, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    body_hash = request_hash({"task_id": task_id, **body.model_dump(mode="json")})
    replay = replay_idempotency(_db(request), idempotency_key, "save_spec", body_hash)
    if replay is not None:
        return _response(replay, 201)
    result = save_spec(_db(request), task_id, body)
    data = result.model_dump(mode="json")
    save_idempotency(_db(request), idempotency_key, "save_spec", body_hash, data)
    return _response(data, 201)


@router.post("/spec-versions/{version_id}/confirm")
def post_confirm_spec(request: Request, version_id: str, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    body_hash = request_hash({"version_id": version_id})
    replay = replay_idempotency(_db(request), idempotency_key, "confirm_spec", body_hash)
    if replay is not None:
        return _response(replay)
    result = confirm_spec(_db(request), version_id)
    data = result.model_dump(mode="json")
    save_idempotency(_db(request), idempotency_key, "confirm_spec", body_hash, data)
    return _response(data)


@router.post("/tasks/{task_id}/rounds", status_code=201)
def post_round(request: Request, task_id: str, body: RoundCreate, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    body_hash = request_hash({"task_id": task_id, **body.model_dump(mode="json")})
    replay = replay_idempotency(_db(request), idempotency_key, "create_round", body_hash)
    if replay is not None:
        return _response(replay, 201)
    result = create_round(_db(request), task_id, body)
    data = result.model_dump(mode="json")
    save_idempotency(_db(request), idempotency_key, "create_round", body_hash, data)
    return _response(data, 201)


@router.post("/tasks/{task_id}/branches", status_code=201)
def post_branch(request: Request, task_id: str, body: BranchCreate = BranchCreate(), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    body_hash = request_hash({"task_id": task_id, **body.model_dump(mode="json")})
    replay = replay_idempotency(_db(request), idempotency_key, "create_branch", body_hash)
    if replay is not None:
        return _response(replay, 201)
    result = create_branch(_db(request), task_id, body)
    data = result.model_dump(mode="json")
    save_idempotency(_db(request), idempotency_key, "create_branch", body_hash, data)
    return _response(data, 201)


@router.post("/rounds/{round_id}/submissions", status_code=201)
async def post_submission(
    request: Request,
    round_id: str,
    files: list[UploadFile] = File(...),
    note: str | None = Form(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    payload = []
    file_contents = []
    for upload in files:
        content = await upload.read()
        file_contents.append((upload.filename, content))
        payload.append({"filename": upload.filename, "sha256": request_hash(content.hex())})
    body_hash = request_hash({"round_id": round_id, "note": note, "files": payload})
    replay = replay_idempotency(_db(request), idempotency_key, "create_submission", body_hash)
    if replay is not None:
        return _response(replay, 201)
    result = upload_submission(_db(request), _settings(request), round_id, file_contents, note)
    data = result.model_dump(mode="json")
    save_idempotency(_db(request), idempotency_key, "create_submission", body_hash, data)
    return _response(data, 201)


@router.delete("/tasks/{task_id}")
def remove_task(request: Request, task_id: str):
    return _response(delete_task(_db(request), _settings(request), task_id))
