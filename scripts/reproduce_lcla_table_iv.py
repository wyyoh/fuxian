#!/usr/bin/env python3
"""运行并汇总 LCLA-AKA Table IV reference benchmark。"""

from __future__ import annotations

# ruff: noqa: I001

import argparse
import csv
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmarks.lcla_benchmark import (
    TABLE_IV_OPERATIONS,
    append_rows,
    run_constructed_static_benchmark,
    run_table_iv_benchmark,
)

_SUMMARY_FIELDS: Final = (
    "profile",
    "backend",
    "keygen_backend",
    "operation",
    "sample_count",
    "measured_failure_count",
    "placeholder_count",
    "mean_ms",
    "median_ms",
    "std_ms",
    "min_ms",
    "max_ms",
    "p95_ms",
    "coefficient_of_variation",
)
_COMPARISON_FIELDS: Final = (
    "profile",
    "backend",
    "paper_operation",
    "paper_time_ms",
    "reproduced_mean_ms",
    "reproduced_median_ms",
    "absolute_error_ms",
    "relative_error_percent",
    "source_printed_page",
    "timing_equivalence",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--mode", choices=("smoke", "exact"), default="smoke")
    parser.add_argument("--warmup", type=int, default=20)
    parser.add_argument("--repetitions", type=int, default=1000)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--aggregate-only", action="store_true")
    parser.add_argument("--raw-output", type=Path)
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=Path("artifacts/processed/LCLA_AKA/table_iv_reproduced.csv"),
    )
    parser.add_argument(
        "--comparison-output",
        type=Path,
        default=Path("artifacts/processed/LCLA_AKA/table_iv_comparison.csv"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("artifacts/processed/LCLA_AKA/table_iv_summary.json"),
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        default=Path("reports/lcla_aka_table_iv_report.md"),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_root = args.repo_root.resolve()
    raw_output = args.raw_output
    if raw_output is None:
        raw_output = (
            Path("artifacts/raw/LCLA_AKA/benchmark_raw.csv")
            if args.mode == "exact"
            else Path("artifacts/processed/LCLA_AKA/benchmark_raw_smoke.csv")
        )
    raw_output = _resolve(repo_root, raw_output)
    repetitions = args.repetitions if args.mode == "exact" else min(args.repetitions, 3)
    warmup = args.warmup if args.mode == "exact" else min(args.warmup, 1)
    if not args.aggregate_only:
        profiles = (
            ["paper_performance", "audited_preserve_keylen", "audited_preserve_dimension"]
            if args.mode == "exact"
            else ["toy", "paper_performance"]
        )
        for index, profile in enumerate(profiles):
            rows = run_table_iv_benchmark(
                repo_root=repo_root,
                profile_name=profile,
                warmup=warmup,
                repetitions=repetitions,
                seed_base=710_000 + index * 100_000,
            )
            rows.extend(
                run_constructed_static_benchmark(
                    repo_root=repo_root,
                    profile_name=profile,
                    warmup=warmup,
                    repetitions=repetitions,
                    seed_base=810_000 + index * 100_000,
                )
            )
            append_rows(raw_output, rows, resume=args.resume or raw_output.exists())
    summary = aggregate_raw(raw_output)
    reference = read_table_iv_reference(
        repo_root / "specs" / "lcla_aka" / "paper_table_iv_reference.csv"
    )
    comparison = compare_reference(summary, reference)
    raw_counts = summarize_measurement_kinds(raw_output)
    payload: dict[str, object] = {
        "schema_version": 1,
        "result": "reference_benchmark_complete_strict_original_timing_not_reproduced",
        "mode": args.mode,
        "warmup": warmup,
        "repetitions": repetitions,
        "paper_frodo_backend_identified": True,
        "paper_frodo_backend_built": True,
        "strict_original_operation_timing_reproduced": False,
        "numpy_reference_benchmark_completed": any(
            row["sample_count"] for row in summary if row["operation"] in TABLE_IV_OPERATIONS
        ),
        "real_trapdoor_benchmark_completed": False,
        "constructed_backend_benchmark_completed": any(
            row["operation"] == "constructed_static_keygen" and row["sample_count"]
            for row in summary
        ),
        "raw_measurement_counts": raw_counts,
        "operation_mapping": "specs/lcla_aka/table_iv_operation_mapping.csv",
    }
    _write_csv(_resolve(repo_root, args.summary_output), summary, _SUMMARY_FIELDS)
    _write_csv(_resolve(repo_root, args.comparison_output), comparison, _COMPARISON_FIELDS)
    json_output = _resolve(repo_root, args.json_output)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_output = _resolve(repo_root, args.report_output)
    report_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.write_text(render_report(payload, comparison), encoding="utf-8")
    print(json.dumps({"result": payload["result"], "raw": str(raw_output)}))
    return 0


def read_table_iv_reference(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if {row["paper_operation"] for row in rows} != set(TABLE_IV_OPERATIONS):
        raise ValueError("Table IV operation 集合与 benchmark 不一致")
    if not all(row["transcription_verified"].lower() == "true" for row in rows):
        raise ValueError("Table IV 存在未人工核对行")
    return rows


def aggregate_raw(path: Path) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            grouped[
                (
                    row["profile"],
                    row["backend"],
                    row["keygen_backend"],
                    row["operation"],
                )
            ].append(row)
    output: list[dict[str, object]] = []
    for (profile, backend, keygen_backend, operation), rows in sorted(grouped.items()):
        successful = [
            row
            for row in rows
            if row["measurement_kind"] == "measured_success" and row["success"].lower() == "true"
        ]
        failures = [row for row in rows if row["measurement_kind"] == "measured_failure"]
        placeholders = [row for row in rows if row["measurement_kind"].endswith("_placeholder")]
        values = [int(row["elapsed_ns"]) / 1_000_000 for row in successful]
        stats = _statistics(values)
        output.append(
            {
                "profile": profile,
                "backend": backend,
                "keygen_backend": keygen_backend,
                "operation": operation,
                "sample_count": len(successful),
                "measured_failure_count": len(failures),
                "placeholder_count": len(placeholders),
                **stats,
            }
        )
    return output


def compare_reference(
    summary: list[dict[str, object]],
    reference: list[dict[str, str]],
) -> list[dict[str, object]]:
    reference_by_operation = {row["paper_operation"]: row for row in reference}
    output: list[dict[str, object]] = []
    for row in summary:
        operation = str(row["operation"])
        if operation not in reference_by_operation or not row["sample_count"]:
            continue
        paper = reference_by_operation[operation]
        paper_ms = float(paper["paper_time_ms"])
        mean_ms = float(str(row["mean_ms"]))
        output.append(
            {
                "profile": row["profile"],
                "backend": row["backend"],
                "paper_operation": operation,
                "paper_time_ms": paper_ms,
                "reproduced_mean_ms": mean_ms,
                "reproduced_median_ms": row["median_ms"],
                "absolute_error_ms": abs(mean_ms - paper_ms),
                "relative_error_percent": abs(mean_ms - paper_ms) / paper_ms * 100,
                "source_printed_page": paper["source_printed_page"],
                "timing_equivalence": "not_strictly_equivalent_numpy_reference",
            }
        )
    return output


def summarize_measurement_kinds(path: Path) -> dict[str, int]:
    counts: Counter[str] = Counter()
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            counts[row["measurement_kind"]] += 1
    return dict(sorted(counts.items()))


def render_report(payload: dict[str, object], rows: list[dict[str, object]]) -> str:
    lines = [
        "# LCLA-AKA Table IV Reference Benchmark",
        "",
        "## 证据边界",
        "",
        "- 论文 Frodo 仓库已识别且 serial build 成功，但没有 LCLA 所需的任意参数、",
        "  Definition 5 reconciliation、TrapGen 或 SamplePre API。",
        "- 本表是 `numpy_reference` 映射；包含 shape/overflow 检查、Python 对象开销、",
        "  canonical 编码和 SHAKE256 开销，不是论文 Frodo 原生操作的严格计时复现。",
        "- `strict_original_operation_timing_reproduced=false`。",
        "- unavailable dependency 使用 placeholder，`actual_execution_attempted=false`，",
        "  不计作独立执行失败。",
        "",
        "## 论文值与 reference 测量",
        "",
        "| profile | operation | paper ms | mean ms | median ms | 相对误差 % |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['profile']} | {row['paper_operation']} | {row['paper_time_ms']} | "
            f"{float(str(row['reproduced_mean_ms'])):.6f} | "
            f"{float(str(row['reproduced_median_ms'])):.6f} | "
            f"{float(str(row['relative_error_percent'])):.2f} |"
        )
    lines.extend(
        [
            "",
            "绝对偏差不只来自硬件环境，还来自 reference 实现的数据结构校验、数组复制、",
            "Python 调用开销、canonical 编码、SHAKE256 以及与论文 Frodo primitive",
            "无法完全同构的 operation mapping。",
            "",
            f"机器状态：`{payload['result']}`。",
            "",
        ]
    )
    return "\n".join(lines)


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
    ordered = sorted(values)
    mean = statistics.fmean(values)
    std = statistics.pstdev(values)
    p95_index = max(0, min(len(ordered) - 1, int(0.95 * len(ordered) + 0.999999) - 1))
    return {
        "mean_ms": mean,
        "median_ms": statistics.median(values),
        "std_ms": std,
        "min_ms": ordered[0],
        "max_ms": ordered[-1],
        "p95_ms": ordered[p95_index],
        "coefficient_of_variation": std / mean if mean else 0.0,
    }


def _write_csv(path: Path, rows: list[dict[str, object]], fields: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


if __name__ == "__main__":
    raise SystemExit(main())
