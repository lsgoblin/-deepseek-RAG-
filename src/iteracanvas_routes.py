"""FastAPI routes for the IteraCanvas phase 2 mock-AI workflow."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, File, Form, Header, Request, UploadFile
from fastapi.responses import JSONResponse

from .iteracanvas_models import (
    AcceptCreate,
    BranchCreate,
    DiagnosisCreate,
    DiagnosisReviewCreate,
    PatchCreate,
    RoundCreate,
    SpecVersionCreate,
    SpecExtractionCreate,
    TaskCreate,
)
from .iteracanvas_services import (
    AppError,
    accept_candidate,
    add_diagnosis_review,
    compare_round,
    confirm_spec,
    create_branch,
    create_round,
    create_patch,
    create_task,
    delete_task,
    get_task,
    get_diagnosis as get_diagnosis_result,
    extract_task_spec,
    list_tasks,
    replay_idempotency,
    request_hash,
    run_diagnosis,
    save_idempotency,
    save_spec,
    start_diagnosis,
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


@router.post("/tasks/{task_id}/spec-extractions")
def post_spec_extraction(request: Request, task_id: str, body: SpecExtractionCreate = SpecExtractionCreate()):
    result = extract_task_spec(_db(request), task_id, body.task_text, body.reference_images)
    return _response(result)


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


@router.post("/candidates/{candidate_id}/diagnoses", status_code=202)
def post_diagnosis(
    request: Request,
    candidate_id: str,
    background_tasks: BackgroundTasks,
    body: DiagnosisCreate = DiagnosisCreate(),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    body_hash = request_hash({"candidate_id": candidate_id, **body.model_dump(mode="json")})
    replay = replay_idempotency(_db(request), idempotency_key, "start_diagnosis", body_hash)
    if replay is not None:
        return _response(replay, 202)
    result = start_diagnosis(_db(request), candidate_id)
    background_tasks.add_task(run_diagnosis, _db(request), result.id, _settings(request).ai_mode)
    data = result.model_dump(mode="json")
    save_idempotency(_db(request), idempotency_key, "start_diagnosis", body_hash, data)
    return _response(data, 202)


@router.get("/diagnoses/{diagnosis_id}")
def get_diagnosis(request: Request, diagnosis_id: str):
    return _response(get_diagnosis_result(_db(request), diagnosis_id))


@router.post("/diagnoses/{diagnosis_id}/reviews", status_code=201)
def post_diagnosis_review(
    request: Request,
    diagnosis_id: str,
    body: DiagnosisReviewCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    body_hash = request_hash({"diagnosis_id": diagnosis_id, **body.model_dump(mode="json")})
    replay = replay_idempotency(_db(request), idempotency_key, "review_diagnosis", body_hash)
    if replay is not None:
        return _response(replay, 201)
    result = add_diagnosis_review(_db(request), diagnosis_id, body)
    data = result.model_dump(mode="json")
    save_idempotency(_db(request), idempotency_key, "review_diagnosis", body_hash, data)
    return _response(data, 201)


@router.post("/rounds/{round_id}/patches", status_code=201)
def post_patch(
    request: Request,
    round_id: str,
    body: PatchCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    body_hash = request_hash({"round_id": round_id, **body.model_dump(mode="json")})
    replay = replay_idempotency(_db(request), idempotency_key, "create_patch", body_hash)
    if replay is not None:
        return _response(replay, 201)
    result = create_patch(_db(request), round_id, body)
    data = result.model_dump(mode="json")
    save_idempotency(_db(request), idempotency_key, "create_patch", body_hash, data)
    return _response(data, 201)


@router.get("/rounds/{round_id}/comparison")
def get_comparison(request: Request, round_id: str):
    return _response(compare_round(_db(request), round_id))


@router.post("/tasks/{task_id}/accept")
def post_accept(
    request: Request,
    task_id: str,
    body: AcceptCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    body_hash = request_hash({"task_id": task_id, **body.model_dump(mode="json")})
    replay = replay_idempotency(_db(request), idempotency_key, "accept_candidate", body_hash)
    if replay is not None:
        return _response(replay)
    result = accept_candidate(_db(request), task_id, body.candidate_id)
    data = result.model_dump(mode="json")
    save_idempotency(_db(request), idempotency_key, "accept_candidate", body_hash, data)
    return _response(data)


@router.delete("/tasks/{task_id}")
def remove_task(request: Request, task_id: str):
    return _response(delete_task(_db(request), _settings(request), task_id))
