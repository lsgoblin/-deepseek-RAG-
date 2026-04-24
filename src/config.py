"""Configuration management for the RAG project.

This module centralizes default values, environment loading, and path
resolution so later modules can import one stable settings object.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache
import os
from pathlib import Path


def _parse_env_file(env_path: Path) -> dict[str, str]:
    """Parse a simple `.env` file into a key-value mapping."""

    if not env_path.exists():
        return {}

    parsed: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        parsed[key.strip()] = value.strip().strip('"').strip("'")

    return parsed


def _to_int(raw_value: str | None, default: int) -> int:
    """Convert a raw string value to `int`, falling back to a default."""

    if raw_value is None or raw_value == "":
        return default
    return int(raw_value)


def _to_float(raw_value: str | None, default: float) -> float:
    """Convert a raw string value to `float`, falling back to a default."""

    if raw_value is None or raw_value == "":
        return default
    return float(raw_value)


@dataclass(frozen=True)
class Settings:
    """Immutable application settings resolved from defaults and `.env`."""

    project_root: Path
    data_dir: Path
    vector_db_dir: Path
    outputs_dir: Path
    screenshots_dir: Path
    experiment_results_dir: Path
    deepseek_api_key: str | None
    deepseek_base_url: str
    deepseek_model: str
    embedding_model: str
    vector_db_type: str
    top_k: int
    chunk_size: int
    chunk_overlap: int
    temperature: float
    max_docs: int

    @classmethod
    def from_env(
        cls,
        project_root: Path | None = None,
        env_file_name: str = ".env",
    ) -> "Settings":
        """Build a settings instance from defaults, `.env`, and OS env vars."""

        resolved_root = project_root or Path(__file__).resolve().parent.parent
        env_from_file = _parse_env_file(resolved_root / env_file_name)

        def read(name: str, default: str | None = None) -> str | None:
            return os.getenv(name, env_from_file.get(name, default))

        data_dir = resolved_root / "data"
        outputs_dir = resolved_root / "outputs"
        vector_db_dir = resolved_root / read("VECTOR_DB_DIR", "./vector_store").lstrip("./")

        return cls(
            project_root=resolved_root,
            data_dir=data_dir,
            vector_db_dir=vector_db_dir,
            outputs_dir=outputs_dir,
            screenshots_dir=outputs_dir / "screenshots",
            experiment_results_dir=outputs_dir / "experiment_results",
            deepseek_api_key=read("DEEPSEEK_API_KEY"),
            deepseek_base_url=read("DEEPSEEK_BASE_URL", "https://api.deepseek.com") or "",
            deepseek_model=read("DEEPSEEK_MODEL", "deepseek-chat") or "",
            embedding_model=read("EMBEDDING_MODEL", "BAAI/bge-small-zh") or "",
            vector_db_type=read("VECTOR_DB_TYPE", "chroma") or "",
            top_k=_to_int(read("TOP_K"), 3),
            chunk_size=_to_int(read("CHUNK_SIZE"), 400),
            chunk_overlap=_to_int(read("CHUNK_OVERLAP"), 80),
            temperature=_to_float(read("TEMPERATURE"), 0.2),
            max_docs=_to_int(read("MAX_DOCS"), 200),
        )

    def as_dict(self) -> dict[str, object]:
        """Expose settings as a plain dictionary."""

        return asdict(self)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings object for application-wide reuse."""

    return Settings.from_env()
