"""Image validation and controlled local file storage."""

from __future__ import annotations

import hashlib
import io
import shutil
import warnings
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from PIL import Image, UnidentifiedImageError

from .iteracanvas_config import Settings


@dataclass(frozen=True)
class ValidatedImage:
    content: bytes
    sha256: str
    image_format: str
    mime_type: str
    width: int
    height: int
    extension: str


@dataclass(frozen=True)
class StoredImage:
    candidate_id: str
    validated: ValidatedImage
    original_path: str
    sanitized_path: str
    created_paths: tuple[Path, Path]


MIME_TYPES = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}
EXTENSIONS = {"PNG": "png", "JPEG": "jpg", "WEBP": "webp"}


class ImageValidationError(ValueError):
    pass


def validate_image(content: bytes, settings: Settings) -> ValidatedImage:
    # 不能只信扩展名或 Content-Type，必须让 Pillow 实际解码并校验图片。
    if not content:
        raise ImageValidationError("图片不能为空")
    if len(content) > settings.max_image_bytes:
        raise ImageValidationError(f"图片超过 {settings.max_image_bytes} 字节限制")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as image:
                image.verify()
            with Image.open(io.BytesIO(content)) as image:
                image_format = (image.format or "").upper()
                width, height = image.size
                if image_format not in settings.supported_image_formats:
                    raise ImageValidationError("仅支持 PNG、JPEG 和 WebP")
                if width * height > settings.max_image_pixels:
                    raise ImageValidationError(f"图片像素超过 {settings.max_image_pixels} 限制")
                image.load()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        if isinstance(exc, ImageValidationError):
            raise
        raise ImageValidationError("文件不是有效图片") from exc

    return ValidatedImage(
        content=content,
        sha256=hashlib.sha256(content).hexdigest(),
        image_format=image_format,
        mime_type=MIME_TYPES[image_format],
        width=width,
        height=height,
        extension=EXTENSIONS[image_format],
    )


def _safe_task_path(settings: Settings, relative_path: str) -> Path:
    root = settings.runtime_dir.resolve()
    path = (settings.runtime_dir / relative_path).resolve()
    if path != root and root not in path.parents:
        raise ValueError("路径越界")
    return path


def task_storage_bytes(settings: Settings, task_id: str) -> int:
    task_dir = _safe_task_path(settings, f"tasks/{task_id}")
    if not task_dir.exists():
        return 0
    return sum(path.stat().st_size for path in task_dir.rglob("*") if path.is_file())


def store_image(settings: Settings, task_id: str, round_id: str, candidate_id: str, image: ValidatedImage) -> StoredImage:
    # 先写 runtime/tmp，验证脱敏副本成功后再原子移动到任务目录。
    task_dir = _safe_task_path(settings, f"tasks/{task_id}")
    original_dir = task_dir / "rounds" / round_id / "originals"
    sanitized_dir = task_dir / "rounds" / round_id / "sanitized"
    original_dir.mkdir(parents=True, exist_ok=True)
    sanitized_dir.mkdir(parents=True, exist_ok=True)
    original = original_dir / f"{candidate_id}.{image.extension}"
    sanitized = sanitized_dir / f"{candidate_id}.{image.extension}"

    settings.tmp_dir.mkdir(parents=True, exist_ok=True)
    temp_original = settings.tmp_dir / f"{uuid4().hex}.upload"
    temp_sanitized = settings.tmp_dir / f"{uuid4().hex}.sanitized"
    temp_original.write_bytes(image.content)
    try:
        with Image.open(io.BytesIO(image.content)) as source:
            image_copy = source.copy()
            if image.image_format == "JPEG" and image_copy.mode not in ("RGB", "L"):
                image_copy = image_copy.convert("RGB")
            save_kwargs = {"exif": b""}
            if image.image_format == "JPEG":
                save_kwargs["quality"] = 95
            image_copy.save(temp_sanitized, format=image.image_format, **save_kwargs)
        temp_original.replace(original)
        temp_sanitized.replace(sanitized)
    except Exception:
        for path in (temp_original, temp_sanitized, original, sanitized):
            path.unlink(missing_ok=True)
        raise

    return StoredImage(
        candidate_id=candidate_id,
        validated=image,
        original_path=original.relative_to(settings.runtime_dir).as_posix(),
        sanitized_path=sanitized.relative_to(settings.runtime_dir).as_posix(),
        created_paths=(original, sanitized),
    )


def remove_paths(paths: list[Path] | tuple[Path, ...]) -> None:
    for path in paths:
        path.unlink(missing_ok=True)


def move_task_to_trash(settings: Settings, task_id: str, job_id: str) -> tuple[Path, Path | None]:
    source = _safe_task_path(settings, f"tasks/{task_id}")
    if not source.exists():
        return source, None
    destination = _safe_task_path(settings, f"trash/{job_id}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(destination))
    return source, destination


def remove_trash(settings: Settings, destination: Path | None) -> None:
    if destination and destination.exists():
        shutil.rmtree(destination)
