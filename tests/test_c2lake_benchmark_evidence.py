from __future__ import annotations

import csv
from pathlib import Path
from typing import cast

from scripts.reproduce_c2lake_table7 import (
    aggregate_raw,
    build_trend_summary,
    summarize_raw_measurements,
)


def test_trend_summary_uses_cross_m_series() -> None:
    comparison_rows: list[dict[str, object]] = [
        _comparison_row(32, 1.0, 10.0),
        _comparison_row(48, 2.0, 20.0),
        _comparison_row(64, 3.0, 40.0),
        _comparison_row(256, 4.0, ""),
    ]

    trend = build_trend_summary(comparison_rows)

    assert len(trend) == 1
    assert trend[0]["completed_point_count"] == 3
    assert trend[0]["spearman_rho"] == 1.0
    assert trend[0]["monotonic_increasing"] is True
    assert cast(str, trend[0]["trend_interpretation"]).endswith("not_absolute_timing_reproduction")
    assert "trend_match" not in comparison_rows[0]


def test_timeout_placeholder_rows_are_not_actual_execution_attempts(tmp_path: Path) -> None:
    raw_path = tmp_path / "raw.csv"
    _write_raw(
        raw_path,
        [
            {
                "profile": "paper_literal_m32",
                "phase": "Setup",
                "success": "True",
                "error_code": "",
                "measurement_kind": "measured_success",
                "actual_execution_attempted": "True",
                "timeout_scope": "",
                "parent_attempt_id": "",
            },
            {
                "profile": "paper_literal_m256",
                "phase": "Setup",
                "success": "False",
                "error_code": "timeout",
                "measurement_kind": "profile_timeout_placeholder",
                "actual_execution_attempted": "False",
                "timeout_scope": "profile_subprocess",
                "parent_attempt_id": "paper_literal_m256:timeout:1",
            },
            {
                "profile": "paper_literal_m256",
                "phase": "full_handshake",
                "success": "False",
                "error_code": "timeout",
                "measurement_kind": "profile_timeout_placeholder",
                "actual_execution_attempted": "False",
                "timeout_scope": "profile_subprocess",
                "parent_attempt_id": "paper_literal_m256:timeout:1",
            },
        ],
    )

    rows = list(csv.DictReader(raw_path.open(newline="", encoding="utf-8")))
    timeout_rows = [row for row in rows if row["measurement_kind"] == "profile_timeout_placeholder"]
    assert timeout_rows
    assert {row["actual_execution_attempted"] for row in timeout_rows} == {"False"}
    assert {row["timeout_scope"] for row in timeout_rows} == {"profile_subprocess"}


def test_timeout_placeholder_count_and_profile_level_timeout_are_separate(tmp_path: Path) -> None:
    raw_path = tmp_path / "raw.csv"
    _write_raw(
        raw_path,
        [
            {
                "profile": "paper_literal_m256",
                "phase": "Setup",
                "success": "False",
                "error_code": "timeout",
                "measurement_kind": "profile_timeout_placeholder",
                "actual_execution_attempted": "False",
                "timeout_scope": "profile_subprocess",
                "parent_attempt_id": "paper_literal_m256:timeout:1",
            },
            {
                "profile": "paper_literal_m256",
                "phase": "full_handshake",
                "success": "False",
                "error_code": "timeout",
                "measurement_kind": "profile_timeout_placeholder",
                "actual_execution_attempted": "False",
                "timeout_scope": "profile_subprocess",
                "parent_attempt_id": "paper_literal_m256:timeout:1",
            },
        ],
    )

    summary = summarize_raw_measurements(raw_path)
    table_rows = aggregate_raw(raw_path)

    assert summary["placeholder_rows"] == 2
    assert summary["profile_level_timeouts"] == 1
    assert summary["timed_out_profiles"] == ["paper_literal_m256"]
    assert sum(cast(int, row["placeholder_count"]) for row in table_rows) == 2
    assert sum(cast(int, row["failed_count"]) for row in table_rows) == 0


def _comparison_row(m: int, paper_ms: float, reproduced_mean_ms: float | str) -> dict[str, object]:
    return {
        "family": "paper_literal",
        "m": m,
        "q": m * m,
        "n": 640,
        "phase": "Setup",
        "timing_boundary": "setup",
        "paper_ms": paper_ms,
        "reproduced_mean_ms": reproduced_mean_ms,
        "reproduced_median_ms": reproduced_mean_ms,
        "absolute_error_ms": "",
        "relative_error_percent": "",
        "source_page": "p15",
    }


def _write_raw(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "protocol",
        "profile",
        "family",
        "m",
        "q",
        "n",
        "phase",
        "repetition",
        "seed",
        "backend",
        "elapsed_ns",
        "success",
        "error_code",
        "git_commit",
        "python_version",
        "numpy_version",
        "cpu",
        "os",
        "timestamp_utc",
        "matrix_numpy_bytes",
        "estimated_peak_bytes",
        "available_memory_bytes",
        "measurement_kind",
        "actual_execution_attempted",
        "timeout_scope",
        "parent_attempt_id",
    ]
    defaults = {
        "protocol": "C2LAKE",
        "family": "paper_literal",
        "m": "256",
        "q": "65536",
        "n": "8192",
        "repetition": "0",
        "seed": "0",
        "backend": "fast",
        "elapsed_ns": "0",
        "git_commit": "test",
        "python_version": "3",
        "numpy_version": "2",
        "cpu": "test",
        "os": "test",
        "timestamp_utc": "2026-01-01T00:00:00Z",
        "matrix_numpy_bytes": "0",
        "estimated_peak_bytes": "0",
        "available_memory_bytes": "0",
    }
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            merged = defaults | row
            writer.writerow(merged)
