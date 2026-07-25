from __future__ import annotations

import csv
from pathlib import Path

from benchmarks.lcla_benchmark import LCLABenchmarkRow
from scripts.reproduce_lcla_figure4 import build_figure_data, build_trend_summary
from scripts.reproduce_lcla_table_iv import read_table_iv_reference
from scripts.reproduce_lcla_table_v import build_table_v_rows

_ROOT = Path(__file__).resolve().parents[1]


def test_table_iv_reference_was_manually_verified() -> None:
    rows = read_table_iv_reference(_ROOT / "specs" / "lcla_aka" / "paper_table_iv_reference.csv")

    assert len(rows) == 15
    assert all(row["source_printed_page"] == "9222" for row in rows)
    assert all(row["transcription_verified"] == "true" for row in rows)


def test_dependency_placeholder_is_not_an_execution_failure() -> None:
    row = LCLABenchmarkRow(
        protocol="LCLA-AKA",
        profile="paper_performance",
        backend="frodo_native",
        keygen_backend="not_applicable",
        operation="frodo_native_lcla_operations",
        phase="dependency_probe",
        repetition=-1,
        seed=0,
        elapsed_ns=0,
        success=False,
        error_code="UNSUPPORTED_PARAMETER_AND_MISSING_LCLA_API",
        measurement_kind="dependency_unavailable_placeholder",
        actual_execution_attempted=False,
        timeout_scope="dependency_probe",
        parent_attempt_id="probe-1",
        git_commit="0" * 40,
        python_version="3.12",
        numpy_version="2.0",
        compiler="test",
        cpu="test",
        os="test",
        timestamp_utc="2026-01-01T00:00:00+00:00",
    )

    assert row.actual_execution_attempted is False
    assert row.measurement_kind.endswith("_placeholder")


def test_table_v_keeps_paper_reconstruction_and_measurement_separate() -> None:
    with (
        (_ROOT / "specs/lcla_aka/paper_table_iv_reference.csv").open(
            encoding="utf-8", newline=""
        ) as handle_iv,
        (_ROOT / "specs/lcla_aka/paper_table_v_reference.csv").open(
            encoding="utf-8", newline=""
        ) as handle_v,
    ):
        reference_iv = list(csv.DictReader(handle_iv))
        reference_v = list(csv.DictReader(handle_v))
    table_iv_rows = [
        {
            "profile": "paper_performance",
            "backend": "numpy_reference",
            "operation": row["paper_operation"],
            "mean_ms": row["paper_time_ms"],
        }
        for row in reference_iv
    ]
    phase_rows: list[dict[str, object]] = [
        {
            "profile": "paper_performance",
            "phase": phase,
            "sample_count": 3,
            "mean_ms": 1.0,
        }
        for phase in (
            "initiator_create",
            "responder_verify_and_reply",
            "initiator_verify_and_finish",
            "responder_finish",
        )
    ]
    rows = build_table_v_rows(
        table_iv_rows=table_iv_rows,
        phase_rows=phase_rows,
        table_iv_reference=reference_iv,
        table_v_reference=reference_v,
    )

    evidence_classes = {row["evidence_class"] for row in rows}
    assert "paper_reported_reference" in evidence_classes
    assert "reconstructed_from_table_iv" in evidence_classes
    assert "actually_measured_protocol_phases" in evidence_classes


def test_figure4_trend_uses_sequence_across_entities() -> None:
    data = build_figure_data(
        [
            {
                "scheme": "LCLA-AKA",
                "profile": "paper_performance",
                "evidence_class": "paper_reported_reference",
                "Sum_ms": "8.448",
            }
        ]
    )
    trends = build_trend_summary(data)

    assert len(data) == 10
    assert "trend_match" not in data[0]
    assert trends[0]["completed_point_count"] == 10
    assert trends[0]["spearman_rho"] == 1.0
