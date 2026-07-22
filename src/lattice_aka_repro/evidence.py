"""运行环境元数据的采集、校验与稳定 JSON 写出。"""

from __future__ import annotations

import json
import platform
import re
import subprocess
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

import numpy as np

from lattice_aka_repro.errors import MetadataValidationError
from lattice_aka_repro.randomness import validate_seed

EVIDENCE_REQUIRED_FIELDS: Final = (
    "task_id",
    "git_commit",
    "profile",
    "backend",
    "seed",
    "python",
    "numpy",
    "os",
    "cpu",
    "timestamp_utc",
    "warmup",
    "repetitions",
)
_TASK_ID_PATTERN: Final = re.compile(r"^T[0-9]{3}$")


@dataclass(frozen=True, slots=True)
class RunMetadata:
    """一次运行所需的 evidence schema 基础字段。"""

    task_id: str
    git_commit: str
    profile: str
    backend: str
    seed: int
    python: str
    numpy: str
    os: str
    cpu: str
    timestamp_utc: str
    warmup: int
    repetitions: int
    git_dirty: bool | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.task_id, str) or not _TASK_ID_PATTERN.fullmatch(self.task_id):
            raise MetadataValidationError("task_id 必须匹配 T 后跟三位数字")
        for field_name, value in (
            ("git_commit", self.git_commit),
            ("profile", self.profile),
            ("backend", self.backend),
            ("python", self.python),
            ("numpy", self.numpy),
            ("os", self.os),
            ("cpu", self.cpu),
        ):
            if not isinstance(value, str) or not value.strip():
                raise MetadataValidationError(f"{field_name} 不得为空")
        validate_seed(self.seed)
        _validate_count("warmup", self.warmup, minimum=0)
        _validate_count("repetitions", self.repetitions, minimum=1)
        if not isinstance(self.timestamp_utc, str):
            raise MetadataValidationError("timestamp_utc 必须是字符串")
        _validate_utc_timestamp(self.timestamp_utc)
        if self.git_dirty is not None and not isinstance(self.git_dirty, bool):
            raise MetadataValidationError("git_dirty 必须是布尔值或 null")


def collect_run_metadata(
    *,
    task_id: str,
    profile: str,
    backend: str,
    seed: int,
    warmup: int,
    repetitions: int,
    repo_root: str | Path = ".",
    timestamp: datetime | None = None,
) -> RunMetadata:
    """采集一次运行的 Git、Python、NumPy、操作系统和 CPU 元数据。"""

    timestamp_utc = _format_utc(timestamp)
    cpu = _read_cpu_description()
    git_commit, git_dirty = _read_git_state(Path(repo_root))
    return RunMetadata(
        task_id=task_id,
        git_commit=git_commit,
        profile=profile,
        backend=backend,
        seed=seed,
        python=platform.python_version(),
        numpy=np.__version__,
        os=platform.platform(),
        cpu=cpu,
        timestamp_utc=timestamp_utc,
        warmup=warmup,
        repetitions=repetitions,
        git_dirty=git_dirty,
    )


def write_metadata_json(metadata: RunMetadata, destination: str | Path) -> Path:
    """以稳定格式写出 JSON，并在需要时创建父目录。"""

    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        asdict(metadata),
        allow_nan=False,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    output.write_text(f"{payload}\n", encoding="utf-8")
    return output


def ensure_artifact_dirs(root: str | Path = "artifacts") -> tuple[Path, Path]:
    """幂等创建 raw 与 processed 运行产物目录。"""

    artifact_root = Path(root)
    raw = artifact_root / "raw"
    processed = artifact_root / "processed"
    raw.mkdir(parents=True, exist_ok=True)
    processed.mkdir(parents=True, exist_ok=True)
    return raw, processed


def _validate_count(field_name: str, value: int, *, minimum: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise MetadataValidationError(f"{field_name} 必须是大于或等于 {minimum} 的整数")


def _validate_utc_timestamp(value: str) -> None:
    if not value.endswith("Z"):
        raise MetadataValidationError("timestamp_utc 必须是以 Z 结尾的 UTC 时间")
    try:
        parsed = datetime.fromisoformat(f"{value[:-1]}+00:00")
    except ValueError as error:
        raise MetadataValidationError("timestamp_utc 不是有效的 ISO 8601 时间") from error
    if parsed.utcoffset() != UTC.utcoffset(parsed):
        raise MetadataValidationError("timestamp_utc 必须使用 UTC")


def _format_utc(value: datetime | None) -> str:
    current = value if value is not None else datetime.now(UTC)
    if current.tzinfo is None or current.utcoffset() is None:
        raise MetadataValidationError("timestamp 必须包含时区")
    return current.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_git_state(repo_root: Path) -> tuple[str, bool | None]:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--verify", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return "UNCOMMITTED", None
    commit = result.stdout.strip()
    if result.returncode != 0 or not commit:
        return "UNCOMMITTED", None
    try:
        status = subprocess.run(
            ["git", "-C", str(repo_root), "status", "--porcelain=v1"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return commit, None
    if status.returncode != 0:
        return commit, None
    return commit, bool(status.stdout.strip())


def _read_cpu_description() -> str:
    try:
        cpuinfo = Path("/proc/cpuinfo").read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        cpuinfo = ""
    cpu_fields: dict[str, str] = {}
    for line in cpuinfo.splitlines():
        key, separator, value = line.partition(":")
        normalized_key = key.strip().lower()
        description = value.strip()
        if separator and normalized_key in {"model name", "hardware", "processor"}:
            cpu_fields.setdefault(normalized_key, description)
    for preferred_key in ("model name", "hardware", "processor"):
        description = cpu_fields.get(preferred_key, "")
        if description and not (preferred_key == "processor" and description.isdigit()):
            return description
    return platform.processor().strip() or platform.machine().strip() or "unknown"
