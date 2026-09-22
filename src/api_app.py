"""IteraCanvas FastAPI application entrypoint."""

from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .iteracanvas_config import Settings
from .iteracanvas_db import Database
from .iteracanvas_routes import router
from .iteracanvas_services import AppError


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    settings.prepare()
    app = FastAPI(title="IteraCanvas API", version="1.0.0")
    app.state.settings = settings
    app.state.db = Database(settings.db_path)
    app.include_router(router)

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request.state.request_id = request.headers.get("X-Request-ID", str(uuid4()))
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        # 所有业务错误保持统一结构，前端无需按路由猜测错误格式。
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message, "details": exc.details, "request_id": request.state.request_id},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"code": "INVALID_REQUEST", "message": "请求参数无效", "details": exc.errors(), "request_id": request.state.request_id},
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"code": "INTERNAL_ERROR", "message": "服务器内部错误", "details": {}, "request_id": request.state.request_id},
        )

    @app.get("/")
    def home():
        return {"name": "IteraCanvas", "phase": 2, "api": "/api/v1", "ai_mode": settings.ai_mode}

    return app


app = create_app()
