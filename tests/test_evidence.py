from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from lattice_aka_repro.errors import MetadataValidationError
from lattice_aka_repro.evidence import (
    EVIDENCE_REQUIRED_FIELDS,
    RunMetadata,
    collect_run_metadata,
    ensure_artifact_dirs,
    write_metadata_json,
)


def test_run_metadata_has_all_evidence_fields() -> None:
    metadata = _metadata()

    assert set(EVIDENCE_REQUIRED_FIELDS).issubset(metadata.__dataclass_fields__)


def test_write_metadata_round_trips_and_creates_parent(tmp_path: Path) -> None:
    destination = tmp_path / "processed" / "T001" / "environment.json"

    written = write_metadata_json(_metadata(), destination)
    document = json.loads(written.read_text(encoding="utf-8"))

    assert written == destination
    assert set(EVIDENCE_REQUIRED_FIELDS).issubset(document)
    assert document["seed"] == 0
    assert written.read_bytes().endswith(b"\n")


def test_collect_metadata_uses_utc_and_nonempty_environment(tmp_path: Path) -> None:
    fixed_time = datetime(2026, 7, 22, 12, 34, 56, tzinfo=UTC)

    metadata = collect_run_metadata(
        task_id="T001",
        profile="not_applicable",
        backend="python",
        seed=0,
        warmup=0,
        repetitions=1,
        repo_root=tmp_path,
        timestamp=fixed_time,
    )

    assert metadata.timestamp_utc == "2026-07-22T12:34:56Z"
    assert metadata.git_commit == "UNCOMMITTED"
    assert metadata.python
    assert metadata.numpy
    assert metadata.os
    assert metadata.cpu


def test_collect_metadata_rejects_naive_timestamp(tmp_path: Path) -> None:
    with pytest.raises(MetadataValidationError) as caught:
        collect_run_metadata(
            task_id="T001",
            profile="not_applicable",
            backend="python",
            seed=0,
            warmup=0,
            repetitions=1,
            repo_root=tmp_path,
            timestamp=datetime(2026, 7, 22),
        )

    assert caught.value.code == "METADATA_INVALID"


def test_collect_metadata_marks_dirty_git_worktree(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-b", "main")
    _git(tmp_path, "config", "user.name", "Test Runner")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    tracked = tmp_path / "tracked.txt"
    tracked.write_text("clean\n", encoding="utf-8")
    _git(tmp_path, "add", "tracked.txt")
    _git(tmp_path, "commit", "-m", "test fixture")
    clean_metadata = collect_run_metadata(
        task_id="T001",
        profile="not_applicable",
        backend="python",
        seed=0,
        warmup=0,
        repetitions=1,
        repo_root=tmp_path,
    )
    tracked.write_text("dirty\n", encoding="utf-8")

    metadata = collect_run_metadata(
        task_id="T001",
        profile="not_applicable",
        backend="python",
        seed=0,
        warmup=0,
        repetitions=1,
        repo_root=tmp_path,
    )

    assert clean_metadata.git_dirty is False
    assert metadata.git_commit == clean_metadata.git_commit
    assert metadata.git_dirty is True


def test_metadata_rejects_non_string_field() -> None:
    with pytest.raises(MetadataValidationError) as caught:
        _metadata(profile=42)  # type: ignore[arg-type]

    assert caught.value.code == "METADATA_INVALID"


@pytest.mark.parametrize(
    ("warmup", "repetitions"),
    [(-1, 1), (0, 0), (True, 1), (0, False)],
)
def test_metadata_rejects_invalid_counts(warmup: int, repetitions: int) -> None:
    with pytest.raises(MetadataValidationError) as caught:
        _metadata(warmup=warmup, repetitions=repetitions)

    assert caught.value.code == "METADATA_INVALID"


def test_artifact_directories_are_created_idempotently(tmp_path: Path) -> None:
    first = ensure_artifact_dirs(tmp_path / "artifacts")
    second = ensure_artifact_dirs(tmp_path / "artifacts")

    assert first == second
    assert all(path.is_dir() for path in first)


def _metadata(
    *, profile: str = "not_applicable", warmup: int = 0, repetitions: int = 1
) -> RunMetadata:
    return RunMetadata(
        task_id="T001",
        git_commit="0123456789abcdef",
        profile=profile,
        backend="python",
        seed=0,
        python="3.11.9",
        numpy="2.0.1",
        os="Test OS",
        cpu="Test CPU",
        timestamp_utc="2026-07-22T12:34:56Z",
        warmup=warmup,
        repetitions=repetitions,
    )


def _git(root: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
