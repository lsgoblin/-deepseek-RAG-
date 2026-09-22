"""Runtime configuration for the IteraCanvas local demo."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    return default if value is None else int(value)


@dataclass(frozen=True)
class Settings:
    ai_mode: str = "mock"
    # 阶段 1 阈值来自工程设计第 15 章；真实供应商接入时只能进一步收紧。
    runtime_dir: Path = PROJECT_ROOT / "runtime"
    supported_image_formats: tuple[str, ...] = ("PNG", "JPEG", "WEBP")
    max_image_bytes: int = 10 * 1024 * 1024
    max_image_pixels: int = 40_000_000
    max_images_per_round: int = 8
    max_images_per_task: int = 50
    task_storage_limit_bytes: int = 500 * 1024 * 1024
    model_timeout_seconds: int = 90
    model_max_retries: int = 2
    model_json_repair_attempts: int = 1
    experiment_max_rounds: int = 6
    diagnosis_poll_interval_seconds: float = 1.5

    @property
    def db_path(self) -> Path:
        return self.runtime_dir / "iteracanvas.db"

    @property
    def tasks_dir(self) -> Path:
        return self.runtime_dir / "tasks"

    @property
    def tmp_dir(self) -> Path:
        return self.runtime_dir / "tmp"

    @property
    def trash_dir(self) -> Path:
        return self.runtime_dir / "trash"

    @classmethod
    def from_env(cls) -> "Settings":
        runtime_dir = Path(os.getenv("ITERACANVAS_RUNTIME_DIR", str(PROJECT_ROOT / "runtime")))
        return cls(
            runtime_dir=runtime_dir,
            ai_mode=os.getenv("AI_MODE", "mock"),
            max_image_bytes=_int_env("MAX_IMAGE_BYTES", 10 * 1024 * 1024),
            max_image_pixels=_int_env("MAX_IMAGE_PIXELS", 40_000_000),
            max_images_per_round=_int_env("MAX_IMAGES_PER_ROUND", 8),
            max_images_per_task=_int_env("MAX_IMAGES_PER_TASK", 50),
            task_storage_limit_bytes=_int_env("TASK_STORAGE_LIMIT_MB", 500) * 1024 * 1024,
            model_timeout_seconds=_int_env("MODEL_TIMEOUT_SECONDS", 90),
            model_max_retries=_int_env("MODEL_MAX_RETRIES", 2),
            model_json_repair_attempts=_int_env("MODEL_JSON_REPAIR_ATTEMPTS", 1),
        )

    def prepare(self) -> None:
        for path in (self.runtime_dir, self.tasks_dir, self.tmp_dir, self.trash_dir):
            path.mkdir(parents=True, exist_ok=True)
