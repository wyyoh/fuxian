#!/usr/bin/env python3
"""重构 LCLA-AKA Table V，并分离论文、Table IV 重算与协议阶段实测。"""

from __future__ import annotations

# ruff: noqa: I001

import argparse
import csv
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmarks.lcla_benchmark import append_rows, run_protocol_phase_benchmark

_TABLE_FIELDS: Final = (
    "scheme",
    "profile",
    "evidence_class",
    "Num_A_ms",
    "Num_B_ms",
    "Sum_ms",
    "Verify_ms",
    "verify_scope",
    "source_printed_page",
    "status",
)
_PHASE_FIELDS: Final = (
    "profile",
    "phase",
    "sample_count",
    "measured_failure_count",
    "mean_ms",
    "median_ms",
    "std_ms",
    "min_ms",
    "max_ms",
    "p95_ms",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--mode", choices=("smoke", "exact"), default="smoke")
    parser.add_argument("--repetitions", type=int, default=100)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--aggregate-only", action="store_true")
    parser.add_argument("--raw-input", type=Path)
    parser.add_argument(
        "--table-iv-input",
        type=Path,
        default=Path("artifacts/processed/LCLA_AKA/table_iv_reproduced.csv"),
    )
    parser.add_argument(
        "--table-output",
        type=Path,
        default=Path("artifacts/processed/LCLA_AKA/table_v_reproduced.csv"),
    )
    parser.add_argument(
        "--phase-output",
        type=Path,
        default=Path("artifacts/processed/LCLA_AKA/table_v_protocol_phases.csv"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("artifacts/processed/LCLA_AKA/table_v_summary.json"),
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        default=Path("reports/lcla_aka_benchmark_report.md"),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_root = args.repo_root.resolve()
    raw_input = args.raw_input
    if raw_input is None:
        raw_input = (
            Path("artifacts/raw/LCLA_AKA/benchmark_raw.csv")
            if args.mode == "exact"
            else Path("artifacts/processed/LCLA_AKA/benchmark_raw_smoke.csv")
        )
    raw_path = _resolve(repo_root, raw_input)
    repetitions = args.repetitions if args.mode == "exact" else min(args.repetitions, 2)
    if not args.aggregate_only:
        profiles = (
            ["paper_performance", "audited_preserve_keylen", "audited_preserve_dimension"]
            if args.mode == "exact"
            else ["toy", "paper_performance"]
        )
        for index, profile in enumerate(profiles):
            rows = run_protocol_phase_benchmark(
                repo_root=repo_root,
                profile_name=profile,
                repetitions=repetitions,
                seed_base=910_000 + index * 500_000,
            )
            append_rows(raw_path, rows, resume=args.resume or raw_path.exists())
    phases = aggregate_protocol_phases(raw_path)
    table_iv_rows = _read_csv(_resolve(repo_root, args.table_iv_input))
    table_rows = build_table_v_rows(
        table_iv_rows=table_iv_rows,
        phase_rows=phases,
        table_iv_reference=_read_csv(
            repo_root / "specs" / "lcla_aka" / "paper_table_iv_reference.csv"
        ),
        table_v_reference=_read_csv(
            repo_root / "specs" / "lcla_aka" / "paper_table_v_reference.csv"
        ),
    )
    payload: dict[str, object] = {
        "schema_version": 1,
        "result": "table_v_reconstructed_with_non_equivalent_reference_measurements",
        "mode": args.mode,
        "protocol_repetitions_requested": repetitions,
        "paper_reported_rows": sum(
            row["evidence_class"] == "paper_reported_reference" for row in table_rows
        ),
        "reconstructed_rows": sum(
            row["evidence_class"] == "reconstructed_from_table_iv" for row in table_rows
        ),
        "actually_measured_protocol_rows": sum(
            row["evidence_class"] == "actually_measured_protocol_phases" for row in table_rows
        ),
        "strict_original_operation_timing_reproduced": False,
        "phase_measurement_includes_reference_validation_overhead": True,
        "verify_phase_isolated": False,
        "paper_table_iv_rounding_discrepancy": {
            "paper_table_v_Num_A_ms": 4.255,
            "table_iv_weighted_Num_A_ms": 4.210,
            "paper_table_v_Num_B_ms": 4.233,
            "table_iv_weighted_Num_B_ms": 4.178,
        },
    }
    _write_csv(_resolve(repo_root, args.table_output), table_rows, _TABLE_FIELDS)
    _write_csv(_resolve(repo_root, args.phase_output), phases, _PHASE_FIELDS)
    json_output = _resolve(repo_root, args.json_output)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_output = _resolve(repo_root, args.report_output)
    report_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.write_text(render_report(payload, table_rows), encoding="utf-8")
    print(json.dumps({"result": payload["result"], "raw": str(raw_path)}))
    return 0


def aggregate_protocol_phases(path: Path) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["operation"] == "constructed_protocol":
                grouped[(row["profile"], row["phase"])].append(row)
    output: list[dict[str, object]] = []
    for (profile, phase), rows in sorted(grouped.items()):
        success = [
            row
            for row in rows
            if row["measurement_kind"] == "measured_success" and row["success"].lower() == "true"
        ]
        failures = [row for row in rows if row["measurement_kind"] == "measured_failure"]
        values = [int(row["elapsed_ns"]) / 1_000_000 for row in success]
        output.append(
            {
                "profile": profile,
                "phase": phase,
                "sample_count": len(success),
                "measured_failure_count": len(failures),
                **_statistics(values),
            }
        )
    return output


def build_table_v_rows(
    *,
    table_iv_rows: list[dict[str, str]],
    phase_rows: list[dict[str, object]],
    table_iv_reference: list[dict[str, str]],
    table_v_reference: list[dict[str, str]],
) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for row in table_v_reference:
        output.append(
            {
                "scheme": row["scheme"],
                "profile": "paper_reference",
                "evidence_class": "paper_reported_reference",
                "Num_A_ms": float(row["Num_A_ms"]),
                "Num_B_ms": float(row["Num_B_ms"]),
                "Sum_ms": float(row["Sum_ms"]),
                "Verify_ms": float(row["Verify_ms"]),
                "verify_scope": "paper_reported",
                "source_printed_page": row["source_printed_page"],
                "status": "reference_only",
            }
        )
    paper_times = {
        row["paper_operation"]: float(row["paper_time_ms"]) for row in table_iv_reference
    }
    num_a, num_b = _weighted_party_costs(paper_times, table_iv_reference)
    verify = (
        paper_times["T_mul1"] + paper_times["T_mod1"] + paper_times["T_Mod"] + paper_times["T_H2"]
    )
    output.append(
        {
            "scheme": "LCLA-AKA",
            "profile": "paper_performance",
            "evidence_class": "reconstructed_from_table_iv",
            "Num_A_ms": num_a,
            "Num_B_ms": num_b,
            "Sum_ms": num_a + num_b,
            "Verify_ms": verify,
            "verify_scope": "reconstructed_C_A_times_s_Mod2_H2_with_mod",
            "source_printed_page": "9222",
            "status": "rounding_and_formula_discrepancy_recorded",
        }
    )
    measured_by_profile: dict[str, dict[str, float]] = defaultdict(dict)
    for phase_row in phase_rows:
        if phase_row["sample_count"]:
            measured_by_profile[str(phase_row["profile"])][str(phase_row["phase"])] = float(
                str(phase_row["mean_ms"])
            )
    profiles = sorted(
        {row["profile"] for row in table_iv_rows if row["backend"] == "numpy_reference"}
    )
    for profile in profiles:
        measured_times = {
            row["operation"]: float(row["mean_ms"])
            for row in table_iv_rows
            if row["profile"] == profile
            and row["backend"] == "numpy_reference"
            and row["operation"] in TABLE_IV_OPERATION_SET
            and row["mean_ms"]
        }
        if len(measured_times) == len(TABLE_IV_OPERATION_SET):
            current_a, current_b = _weighted_party_costs(measured_times, table_iv_reference)
            current_verify = (
                measured_times["T_mul1"]
                + measured_times["T_mod1"]
                + measured_times["T_Mod"]
                + measured_times["T_H2"]
            )
            output.append(
                {
                    "scheme": "LCLA-AKA",
                    "profile": profile,
                    "evidence_class": "numpy_reference_reconstructed_from_operations",
                    "Num_A_ms": current_a,
                    "Num_B_ms": current_b,
                    "Sum_ms": current_a + current_b,
                    "Verify_ms": current_verify,
                    "verify_scope": "reference_operation_formula_not_native",
                    "source_printed_page": "",
                    "status": "non_equivalent_reference_measurement",
                }
            )
        phases = measured_by_profile.get(profile, {})
        required = {
            "initiator_create",
            "responder_verify_and_reply",
            "initiator_verify_and_finish",
            "responder_finish",
        }
        if required <= phases.keys():
            alice_total = phases["initiator_create"] + phases["initiator_verify_and_finish"]
            bob_total = phases["responder_verify_and_reply"] + phases["responder_finish"]
            output.append(
                {
                    "scheme": "LCLA-AKA",
                    "profile": profile,
                    "evidence_class": "actually_measured_protocol_phases",
                    "Num_A_ms": alice_total,
                    "Num_B_ms": bob_total,
                    "Sum_ms": alice_total + bob_total,
                    "Verify_ms": "",
                    "verify_scope": "not_isolated_from_reply_or_finish",
                    "source_printed_page": "",
                    "status": "accepted_seed_schedule_validation_overhead_included",
                }
            )
    return output


TABLE_IV_OPERATION_SET: Final = {
    "T_mul0",
    "T_mul1",
    "T_mul2",
    "T_add0",
    "T_add1",
    "T_Samp0",
    "T_Samp1",
    "T_Samp2",
    "T_xor",
    "T_H2",
    "T_H1",
    "T_mod0",
    "T_mod1",
    "T_Sign",
    "T_Mod",
}


def _weighted_party_costs(
    times: dict[str, float],
    reference: list[dict[str, str]],
) -> tuple[float, float]:
    num_a = sum(times[row["paper_operation"]] * int(row["Num_A"]) for row in reference)
    num_b = sum(times[row["paper_operation"]] * int(row["Num_B"]) for row in reference)
    return num_a, num_b


def render_report(payload: dict[str, object], rows: list[dict[str, object]]) -> str:
    lines = [
        "# LCLA-AKA Table IV、Table V 与 Reference Benchmark",
        "",
        "## 实现口径",
        "",
        "- `benchmark_class=auditable_python_reference_implementation`。",
        "- FrodoKEM serial build 成功，但未提供 LCLA 所需任意参数、TrapGen、SamplePre、",
        "  S/Mod2；所以 `strict_original_operation_timing_reproduced=false`。",
        "- NumPy reference 包含 dataclass/shape/domain/overflow 检查、数组复制、",
        "  canonical hash encoding、SHAKE256、Python 对象与函数调用开销。",
        "- constructed phase 计时只选取预先确认可接受的 seed；seed 搜索不计时，",
        "  当前协议 API 内的静态关系验证开销会计入。",
        "",
        "## Table V 分层结果",
        "",
        "| scheme | profile | evidence | Num_A ms | Num_B ms | Sum ms | Verify ms |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['scheme']} | {row['profile']} | {row['evidence_class']} | "
            f"{row['Num_A_ms']} | {row['Num_B_ms']} | {row['Sum_ms']} | "
            f"{row['Verify_ms']} |"
        )
    lines.extend(
        [
            "",
            "由 Table IV 三位小数逐项乘 Num_A/Num_B 后得到 4.210/4.178 ms，",
            "与 Table V 的 4.255/4.233 ms 不一致；可能来自未显示的小数、额外开销或排版。",
            "两组值并列保留。Verify 的 Table IV 重构公式也标明 scope，不能与论文值混同。",
            "",
            "协议 phase 的 Bob verification 与 reply、Bob finish 未被进一步拆开，",
            "因此 actually measured 行不伪造独立 Verify 数值。",
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
        }
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(0.95 * len(ordered) + 0.999999) - 1))
    return {
        "mean_ms": statistics.fmean(values),
        "median_ms": statistics.median(values),
        "std_ms": statistics.pstdev(values),
        "min_ms": ordered[0],
        "max_ms": ordered[-1],
        "p95_ms": ordered[index],
    }


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, object]], fields: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


if __name__ == "__main__":
    raise SystemExit(main())
