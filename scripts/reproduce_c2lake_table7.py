"""运行/汇总 C2LAKE Table 7 计时复现实验。"""

from __future__ import annotations

import argparse
import csv
import platform
import statistics
import subprocess
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, TypeAlias

import numpy as np

from lattice_aka_repro.c2lake_core import C2LakeProfile, load_c2lake_profile
from lattice_aka_repro.c2lake_cost_model import load_profile_names

_PHASES: Final = (
    "Setup",
    "SetSecretValue",
    "PartialPrivateKeyExtract",
    "initiator_create",
    "responder_verify_and_reply",
    "initiator_verify_and_finish",
    "responder_total",
    "initiator_total",
    "full_handshake",
)
_RAW_FIELDS: Final = (
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
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--mode", choices=("smoke", "exact"), default="exact")
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--repetitions", type=int, default=100)
    parser.add_argument("--backend", choices=("safe", "fast"), default="fast")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--aggregate-only",
        action="store_true",
        help="只从已有 raw CSV 重新生成 processed 输出，不启动 benchmark 子进程。",
    )
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument(
        "--raw-output",
        type=Path,
        default=Path("artifacts/raw/C2LAKE/benchmark_raw.csv"),
    )
    parser.add_argument(
        "--table-output",
        type=Path,
        default=Path("artifacts/processed/C2LAKE/table7_reproduced.csv"),
    )
    parser.add_argument(
        "--comparison-output",
        type=Path,
        default=Path("artifacts/processed/C2LAKE/table7_comparison.csv"),
    )
    parser.add_argument(
        "--trend-output",
        type=Path,
        default=Path("artifacts/processed/C2LAKE/table7_trend_summary.csv"),
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        default=Path("reports/c2lake_benchmark_report.md"),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.raw_output.exists() and not args.resume and not args.aggregate_only:
        raise FileExistsError(f"{args.raw_output} 已存在；使用 --resume 避免覆盖")
    args.raw_output.parent.mkdir(parents=True, exist_ok=True)
    if not args.aggregate_only:
        profiles = _profiles_for_mode(args.repo_root / "specs", args.mode)
        for profile in profiles:
            _run_profile_subprocess(args, profile)
    table_rows = aggregate_raw(args.raw_output)
    comparison_rows = compare_with_paper_reference(
        table_rows,
        args.repo_root / "specs" / "c2lake" / "paper_table7_reference.csv",
    )
    trend_rows = build_trend_summary(comparison_rows)
    _write_csv(args.table_output, table_rows, _TABLE_FIELDS)
    _write_csv(args.comparison_output, comparison_rows, _COMPARISON_FIELDS)
    _write_csv(args.trend_output, trend_rows, _TREND_FIELDS)
    _write_report(args.report_output, table_rows, comparison_rows, trend_rows, mode=args.mode)
    print(args.raw_output)
    print(args.table_output)
    print(args.comparison_output)
    print(args.trend_output)
    print(args.report_output)
    return 0


_TABLE_FIELDS: Final = (
    "protocol",
    "profile",
    "family",
    "m",
    "q",
    "n",
    "phase",
    "backend",
    "sample_count",
    "failed_count",
    "placeholder_count",
    "mean_ms",
    "median_ms",
    "std_ms",
    "min_ms",
    "max_ms",
    "p95_ms",
    "coefficient_of_variation",
    "completed",
    "error_codes",
    "measurement_kind_counts",
)
_COMPARISON_FIELDS: Final = (
    "family",
    "m",
    "q",
    "n",
    "phase",
    "timing_boundary",
    "paper_ms",
    "reproduced_mean_ms",
    "reproduced_median_ms",
    "absolute_error_ms",
    "relative_error_percent",
    "source_page",
)
_TREND_FIELDS: Final = (
    "family",
    "phase",
    "timing_boundary",
    "completed_point_count",
    "spearman_rho",
    "monotonic_increasing",
    "paper_monotonic_increasing",
    "reproduced_monotonic_increasing",
    "trend_interpretation",
)
ReferenceRow: TypeAlias = dict[str, int | float | str]


def aggregate_raw(raw_path: Path) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    with raw_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            grouped[(row["profile"], row["phase"], row["backend"])].append(row)

    output: list[dict[str, object]] = []
    for (_profile, _phase, _backend), rows in sorted(grouped.items()):
        success_rows = [
            row
            for row in rows
            if _measurement_kind(row) == "measured_success" and _bool(row["success"])
        ]
        measured_failure_rows = [
            row for row in rows if _measurement_kind(row) == "measured_failure"
        ]
        placeholder_rows = [
            row
            for row in rows
            if _measurement_kind(row)
            in {"profile_timeout_placeholder", "resource_limit_placeholder"}
        ]
        elapsed_ms = [int(row["elapsed_ns"]) / 1_000_000 for row in success_rows]
        first = rows[0]
        failed_count = len(measured_failure_rows)
        placeholder_count = len(placeholder_rows)
        stats = _statistics(elapsed_ms)
        measurement_kind_counts = _measurement_kind_counts(rows)
        output.append(
            {
                "protocol": first["protocol"],
                "profile": first["profile"],
                "family": first["family"],
                "m": int(first["m"]),
                "q": int(first["q"]),
                "n": int(first["n"]),
                "phase": first["phase"],
                "backend": first["backend"],
                "sample_count": len(success_rows),
                "failed_count": failed_count,
                "placeholder_count": placeholder_count,
                "mean_ms": stats["mean_ms"],
                "median_ms": stats["median_ms"],
                "std_ms": stats["std_ms"],
                "min_ms": stats["min_ms"],
                "max_ms": stats["max_ms"],
                "p95_ms": stats["p95_ms"],
                "coefficient_of_variation": stats["coefficient_of_variation"],
                "completed": failed_count == 0 and placeholder_count == 0 and bool(success_rows),
                "error_codes": ";".join(
                    sorted({row["error_code"] for row in rows if row["error_code"]})
                ),
                "measurement_kind_counts": ";".join(
                    f"{key}:{value}" for key, value in sorted(measurement_kind_counts.items())
                ),
            }
        )
    return output


def summarize_raw_measurements(raw_path: Path) -> dict[str, object]:
    if not raw_path.is_file():
        return {
            "actual_measured_success_rows": 0,
            "actual_measured_failure_rows": 0,
            "placeholder_rows": 0,
            "profile_level_timeouts": 0,
            "timed_out_profiles": [],
        }
    actual_measured_success_rows = 0
    actual_measured_failure_rows = 0
    placeholder_rows = 0
    timeout_parent_ids: set[str] = set()
    timed_out_profiles: set[str] = set()
    with raw_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            kind = _measurement_kind(row)
            if kind == "measured_success" and _bool(row["success"]):
                actual_measured_success_rows += 1
            elif kind == "measured_failure":
                actual_measured_failure_rows += 1
            elif kind in {"profile_timeout_placeholder", "resource_limit_placeholder"}:
                placeholder_rows += 1
                if kind == "profile_timeout_placeholder":
                    timeout_parent_ids.add(row.get("parent_attempt_id", row["profile"]))
                    timed_out_profiles.add(row["profile"])
    return {
        "actual_measured_success_rows": actual_measured_success_rows,
        "actual_measured_failure_rows": actual_measured_failure_rows,
        "placeholder_rows": placeholder_rows,
        "profile_level_timeouts": len(timeout_parent_ids),
        "timed_out_profiles": sorted(timed_out_profiles),
    }


def compare_with_paper_reference(
    table_rows: list[dict[str, object]],
    reference_path: Path,
) -> list[dict[str, object]]:
    stats_by_key = {
        (str(row["profile"]), str(row["phase"])): row
        for row in table_rows
        if _as_int(row["sample_count"]) > 0
    }
    references = _read_reference(reference_path)
    comparisons: list[dict[str, object]] = []
    metric_map = (
        ("Setup", "setup_ms", "setup"),
        ("SetSecretValue", "set_secret_value_ms", "set_secret_value"),
        (
            "PartialPrivateKeyExtract",
            "partial_private_key_extract_ms",
            "partial_private_key_extract",
        ),
    )
    for reference in references:
        for family in ("paper_literal", "audited_prime"):
            profile = f"{family}_m{reference['m']}"
            for phase, paper_field, boundary in metric_map:
                comparisons.append(
                    _comparison_row(
                        reference,
                        stats_by_key.get((profile, phase)),
                        family,
                        phase,
                        paper_field,
                        boundary,
                    )
                )
            for boundary in ("initiator_total", "responder_total", "full_handshake"):
                comparisons.append(
                    _comparison_row(
                        reference,
                        stats_by_key.get((profile, boundary)),
                        family,
                        "Key_Agreement",
                        "key_agreement_ms",
                        boundary,
                    )
                )
    return comparisons


def build_trend_summary(comparison_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in comparison_rows:
        grouped[
            (
                str(row["family"]),
                str(row["phase"]),
                str(row["timing_boundary"]),
            )
        ].append(row)
    trend_rows: list[dict[str, object]] = []
    for (family, phase, boundary), rows in sorted(grouped.items()):
        completed = [
            row
            for row in sorted(rows, key=lambda item: _as_int(item["m"]))
            if row["reproduced_mean_ms"] != ""
        ]
        paper_values = [_as_float(row["paper_ms"]) for row in completed]
        reproduced_values = [_as_float(row["reproduced_mean_ms"]) for row in completed]
        if len(completed) < 3:
            trend_rows.append(
                {
                    "family": family,
                    "phase": phase,
                    "timing_boundary": boundary,
                    "completed_point_count": len(completed),
                    "spearman_rho": "",
                    "monotonic_increasing": "",
                    "paper_monotonic_increasing": "",
                    "reproduced_monotonic_increasing": "",
                    "trend_interpretation": "insufficient_completed_points",
                }
            )
            continue
        paper_monotonic = _monotonic_increasing(paper_values)
        reproduced_monotonic = _monotonic_increasing(reproduced_values)
        trend_rows.append(
            {
                "family": family,
                "phase": phase,
                "timing_boundary": boundary,
                "completed_point_count": len(completed),
                "spearman_rho": _spearman_rho(paper_values, reproduced_values),
                "monotonic_increasing": paper_monotonic and reproduced_monotonic,
                "paper_monotonic_increasing": paper_monotonic,
                "reproduced_monotonic_increasing": reproduced_monotonic,
                "trend_interpretation": (
                    "spearman_trend_correlation_only_not_absolute_timing_reproduction"
                ),
            }
        )
    return trend_rows


def _run_profile_subprocess(args: argparse.Namespace, profile: C2LakeProfile) -> None:
    command = [
        sys.executable,
        "benchmarks/c2lake_benchmark.py",
        "--repo-root",
        str(args.repo_root),
        "--profile",
        profile.name,
        "--backend",
        args.backend,
        "--warmup",
        str(args.warmup),
        "--repetitions",
        str(args.repetitions),
        "--raw-output",
        str(args.raw_output),
        "--mode",
        args.mode,
    ]
    if args.resume or args.raw_output.exists():
        command.append("--resume")
    try:
        subprocess.run(command, cwd=args.repo_root, check=False, timeout=args.timeout_seconds)
    except subprocess.TimeoutExpired:
        _append_timeout_failure_rows(args, profile)


def _append_timeout_failure_rows(args: argparse.Namespace, profile: C2LakeProfile) -> None:
    args.raw_output.parent.mkdir(parents=True, exist_ok=True)
    write_header = not args.raw_output.exists()
    environment = _environment(args.repo_root)
    timestamp = _timestamp_utc()
    parent_attempt_id = f"{profile.name}:profile_timeout:{environment['git_commit']}:{timestamp}"
    with args.raw_output.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(_RAW_FIELDS))
        if write_header:
            writer.writeheader()
        for repetition in range(args.repetitions):
            for phase in _PHASES:
                writer.writerow(
                    {
                        "protocol": "C2LAKE",
                        "profile": profile.name,
                        "family": profile.family,
                        "m": profile.m,
                        "q": profile.q,
                        "n": profile.n,
                        "phase": phase,
                        "repetition": repetition,
                        "seed": 0,
                        "backend": args.backend,
                        "elapsed_ns": 0,
                        "success": False,
                        "error_code": "timeout",
                        "git_commit": environment["git_commit"],
                        "python_version": environment["python_version"],
                        "numpy_version": environment["numpy_version"],
                        "cpu": environment["cpu"],
                        "os": environment["os"],
                        "timestamp_utc": timestamp,
                        "matrix_numpy_bytes": profile.n * profile.n * 8,
                        "estimated_peak_bytes": profile.n * profile.n * 16 + 80 * profile.n * 8,
                        "available_memory_bytes": _available_memory_bytes() or "",
                        "measurement_kind": "profile_timeout_placeholder",
                        "actual_execution_attempted": False,
                        "timeout_scope": "profile_subprocess",
                        "parent_attempt_id": parent_attempt_id,
                    }
                )


def _profiles_for_mode(specs_dir: Path, mode: str) -> list[C2LakeProfile]:
    names = load_profile_names(specs_dir=specs_dir)
    profiles = [load_c2lake_profile(name, specs_dir=specs_dir) for name in names]
    if mode == "smoke":
        selected = {"toy", "paper_literal_m32", "audited_prime_m32"}
        return sorted(
            (profile for profile in profiles if profile.name in selected), key=_profile_sort_key
        )
    return sorted(
        (
            profile
            for profile in profiles
            if profile.family in {"paper_literal", "audited_prime"} and profile.name != "toy"
        ),
        key=_profile_sort_key,
    )


def _profile_sort_key(profile: C2LakeProfile) -> tuple[int, str]:
    family_order = "0" if profile.family == "paper_literal" else "1"
    return profile.m, family_order


def _statistics(values: list[float]) -> dict[str, float | str]:
    if not values:
        return {
            "mean_ms": "",
            "median_ms": "",
            "std_ms": "",
            "min_ms": "",
            "max_ms": "",
            "p95_ms": "",
            "coefficient_of_variation": "",
        }
    mean = statistics.fmean(values)
    std = statistics.stdev(values) if len(values) > 1 else 0.0
    return {
        "mean_ms": mean,
        "median_ms": statistics.median(values),
        "std_ms": std,
        "min_ms": min(values),
        "max_ms": max(values),
        "p95_ms": _percentile(values, 95),
        "coefficient_of_variation": std / mean if mean else 0.0,
    }


def _percentile(values: list[float], percentile: int) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((percentile / 100) * (len(ordered) - 1))))
    return ordered[index]


def _read_reference(path: Path) -> list[ReferenceRow]:
    rows: list[ReferenceRow] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows.append(
                {
                    "m": int(row["m"]),
                    "q": int(row["q"]),
                    "n": int(row["n"]),
                    "setup_ms": float(row["setup_ms"]),
                    "set_secret_value_ms": float(row["set_secret_value_ms"]),
                    "partial_private_key_extract_ms": float(row["partial_private_key_extract_ms"]),
                    "key_agreement_ms": float(row["key_agreement_ms"]),
                    "source_page": row["source_page"],
                }
            )
    return rows


def _comparison_row(
    reference: ReferenceRow,
    reproduced: dict[str, object] | None,
    family: str,
    phase: str,
    paper_field: str,
    boundary: str,
) -> dict[str, object]:
    paper_ms = _as_float(reference[paper_field])
    q = _as_int(reproduced["q"]) if reproduced is not None else _as_int(reference["q"])
    n = _as_int(reproduced["n"]) if reproduced is not None else _as_int(reference["n"])
    if reproduced is None:
        return {
            "family": family,
            "m": reference["m"],
            "q": q,
            "n": n,
            "phase": phase,
            "timing_boundary": boundary,
            "paper_ms": paper_ms,
            "reproduced_mean_ms": "",
            "reproduced_median_ms": "",
            "absolute_error_ms": "",
            "relative_error_percent": "",
            "source_page": reference["source_page"],
        }
    mean_ms = _as_float(reproduced["mean_ms"])
    median_ms = _as_float(reproduced["median_ms"])
    absolute = mean_ms - paper_ms
    return {
        "family": family,
        "m": reference["m"],
        "q": q,
        "n": n,
        "phase": phase,
        "timing_boundary": boundary,
        "paper_ms": paper_ms,
        "reproduced_mean_ms": mean_ms,
        "reproduced_median_ms": median_ms,
        "absolute_error_ms": absolute,
        "relative_error_percent": (absolute / paper_ms) * 100 if paper_ms else "",
        "source_page": reference["source_page"],
    }


def _monotonic_increasing(values: list[float]) -> bool:
    return all(values[index] >= values[index - 1] for index in range(1, len(values)))


def _spearman_rho(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or len(left) < 2:
        raise ValueError("Spearman rho 至少需要两个等长序列")
    left_ranks = _average_ranks(left)
    right_ranks = _average_ranks(right)
    left_mean = statistics.fmean(left_ranks)
    right_mean = statistics.fmean(right_ranks)
    numerator = sum(
        (left_value - left_mean) * (right_value - right_mean)
        for left_value, right_value in zip(left_ranks, right_ranks, strict=True)
    )
    left_denominator = sum((value - left_mean) ** 2 for value in left_ranks)
    right_denominator = sum((value - right_mean) ** 2 for value in right_ranks)
    if left_denominator == 0 or right_denominator == 0:
        return 0.0
    return float(numerator / (left_denominator * right_denominator) ** 0.5)


def _average_ranks(values: list[float]) -> list[float]:
    ordered = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end][1] == ordered[index][1]:
            end += 1
        average_rank = (index + 1 + end) / 2
        for original_index, _value in ordered[index:end]:
            ranks[original_index] = average_rank
        index = end
    return ranks


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: tuple[str, ...]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
        writer.writeheader()
        writer.writerows(rows)
    return path


def _write_report(
    path: Path,
    table_rows: list[dict[str, object]],
    comparison_rows: list[dict[str, object]],
    trend_rows: list[dict[str, object]],
    *,
    mode: str,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    completed_profiles = sorted(
        {
            str(row["profile"])
            for row in table_rows
            if bool(row["completed"]) and str(row["phase"]) == "full_handshake"
        }
    )
    incomplete_profiles = sorted(
        {
            str(row["profile"])
            for row in table_rows
            if not bool(row["completed"]) and str(row["phase"]) == "full_handshake"
        }
    )
    actual_measured_success_rows = sum(_as_int(row["sample_count"]) for row in table_rows)
    actual_measured_failure_rows = sum(_as_int(row["failed_count"]) for row in table_rows)
    placeholder_rows = sum(_as_int(row["placeholder_count"]) for row in table_rows)
    timed_out_profiles = sorted(
        {
            str(row["profile"])
            for row in table_rows
            if "timeout" in str(row["error_codes"]) and _as_int(row["placeholder_count"]) > 0
        }
    )
    lines = [
        "# C2LAKE Table 7 / Figure 4 Benchmark Report",
        "",
        "## Summary",
        "",
        f"- mode: {mode}",
        "- benchmark_class: auditable_python_reference_implementation",
        "- algorithmic_workflow_reproduced: true",
        "- reference_implementation_benchmark_completed: partial",
        "- strict_original_implementation_timing_reproduced: false",
        "- m256_completed: false",
        f"- completed_profiles: {', '.join(completed_profiles) if completed_profiles else 'none'}",
        (
            "- incomplete_profiles: "
            f"{', '.join(incomplete_profiles) if incomplete_profiles else 'none'}"
        ),
        f"- actual_measured_success_rows: {actual_measured_success_rows}",
        f"- actual_measured_failure_rows: {actual_measured_failure_rows}",
        f"- placeholder_rows: {placeholder_rows}",
        f"- profile_level_timeouts: {len(timed_out_profiles)}",
        f"- timed_out_profiles: {', '.join(timed_out_profiles) if timed_out_profiles else 'none'}",
        (
            "- Key_Agreement timing boundary is ambiguous in the paper; "
            "initiator_total, responder_total and full_handshake are reported separately."
        ),
        (
            "- Current timing includes reference-implementation overhead: dataclass validation, "
            "array copy/read-only conversion, shape/dtype/domain validation, "
            "canonical hash encoding, SHAKE256 processing, transcript hashing, "
            "optional audited KDF, and Python object/function overhead."
        ),
        "- Raw benchmark rows are never overwritten; reruns require --resume.",
        "",
        "## Reproduced Table 7 Statistics",
        "",
        (
            "| profile | phase | samples | measured failures | placeholders | "
            "mean_ms | median_ms | cv |"
        ),
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in table_rows:
        if row["phase"] in {
            "Setup",
            "SetSecretValue",
            "PartialPrivateKeyExtract",
            "initiator_total",
            "responder_total",
            "full_handshake",
        }:
            lines.append(
                (
                    "| {profile} | {phase} | {samples} | {failed} | {placeholders} | "
                    "{mean} | {median} | {cv} |"
                ).format(
                    profile=row["profile"],
                    phase=row["phase"],
                    samples=row["sample_count"],
                    failed=row["failed_count"],
                    placeholders=row["placeholder_count"],
                    mean=row["mean_ms"],
                    median=row["median_ms"],
                    cv=row["coefficient_of_variation"],
                )
            )
    lines.extend(
        [
            "",
            "## Paper Comparison",
            "",
            "| family | m | phase | boundary | paper_ms | reproduced_mean_ms | rel_error_% |",
            "| --- | ---: | --- | --- | ---: | ---: | ---: |",
        ]
    )
    for row in comparison_rows:
        lines.append(
            "| {family} | {m} | {phase} | {boundary} | {paper} | {mean} | {relative} |".format(
                family=row["family"],
                m=row["m"],
                phase=row["phase"],
                boundary=row["timing_boundary"],
                paper=row["paper_ms"],
                mean=row["reproduced_mean_ms"],
                relative=row["relative_error_percent"],
            )
        )
    lines.extend(
        [
            "",
            "## Trend Summary",
            "",
            (
                "Spearman rho is computed across completed m points only. "
                "It indicates trend correlation, not successful reproduction of absolute timings."
            ),
            "",
            "| family | phase | boundary | points | spearman_rho | monotonic | interpretation |",
            "| --- | --- | --- | ---: | ---: | --- | --- |",
        ]
    )
    for row in trend_rows:
        lines.append(
            (
                "| {family} | {phase} | {boundary} | {points} | {rho} | {monotonic} | "
                "{interpretation} |"
            ).format(
                family=row["family"],
                phase=row["phase"],
                boundary=row["timing_boundary"],
                points=row["completed_point_count"],
                rho=row["spearman_rho"],
                monotonic=row["monotonic_increasing"],
                interpretation=row["trend_interpretation"],
            )
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _bool(value: str) -> bool:
    return value == "True" or value == "true"


def _measurement_kind(row: dict[str, str]) -> str:
    explicit = row.get("measurement_kind", "")
    if explicit:
        return explicit
    if _bool(row.get("success", "")):
        return "measured_success"
    if row.get("error_code") == "timeout":
        return "profile_timeout_placeholder"
    if row.get("error_code") == "resource_limited":
        return "resource_limit_placeholder"
    return "measured_failure"


def _measurement_kind_counts(rows: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[_measurement_kind(row)] += 1
    return counts


def _as_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"expected int, got {value!r}")
    return value


def _as_float(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"expected float-compatible number, got {value!r}")
    return float(value)


def _environment(repo_root: Path) -> dict[str, str]:
    return {
        "git_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            text=True,
        ).strip(),
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "cpu": _cpu_description(),
        "os": platform.platform(),
    }


def _cpu_description() -> str:
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        for line in cpuinfo.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.lower().startswith("model name"):
                return line.split(":", 1)[1].strip()
    return platform.processor() or "unknown"


def _available_memory_bytes() -> int | None:
    meminfo = Path("/proc/meminfo")
    if not meminfo.is_file():
        return None
    for line in meminfo.read_text(encoding="utf-8").splitlines():
        if line.startswith("MemAvailable:"):
            parts = line.split()
            if len(parts) >= 2:
                return int(parts[1]) * 1024
    return None


def _timestamp_utc() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
