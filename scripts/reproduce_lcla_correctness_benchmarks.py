#!/usr/bin/env python3
"""重跑受分布修订影响的 LCLA Gaussian 与协议计时。"""

from __future__ import annotations

# ruff: noqa: I001

import argparse
import csv
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmarks.lcla_benchmark import (
    append_rows,
    run_retry_until_success_benchmark,
    run_table_iv_benchmark,
    run_unconditioned_attempt_benchmark,
)
from lattice_aka_repro.lcla_types import DistributionVariant

PROFILES = (
    "toy",
    "paper_correctness",
    "paper_performance",
    "audited_preserve_keylen",
    "audited_preserve_dimension",
)
VARIANTS: tuple[DistributionVariant, ...] = (
    "paper_literal_distribution",
    "proof_consistent_small_secret",
)
SAMPLING_OPERATIONS = ("T_Samp0", "T_Samp1", "T_Samp2")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--mode", choices=("smoke", "exact"), default="exact")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--raw-output",
        type=Path,
        default=Path("artifacts/raw/LCLA_AKA/correctness_patch_benchmark_raw.csv"),
    )
    parser.add_argument(
        "--correctness-input",
        type=Path,
        default=Path("artifacts/processed/LCLA_AKA/unconditioned_correctness_summary.json"),
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=Path("artifacts/processed/LCLA_AKA/correctness_patch_benchmark_summary.csv"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("artifacts/processed/LCLA_AKA/correctness_patch_benchmark_summary.json"),
    )
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    raw_output = _resolve(repo_root, args.raw_output)
    sampling_warmup = 1 if args.mode == "smoke" else 20
    sampling_repetitions = 2 if args.mode == "smoke" else 1000
    unconditioned_repetitions = 3 if args.mode == "smoke" else 100
    retry_repetitions = 1
    retry_limit = 20 if args.mode == "smoke" else 1000

    rows = []
    for variant_index, variant in enumerate(VARIANTS):
        rows.extend(
            run_table_iv_benchmark(
                repo_root=repo_root,
                profile_name="paper_performance",
                warmup=sampling_warmup,
                repetitions=sampling_repetitions,
                seed_base=50_000_000 + variant_index * 2_000_000,
                distribution_variant=variant,
                operations=SAMPLING_OPERATIONS,
            )
        )
    for profile_index, profile in enumerate(PROFILES):
        for variant_index, variant in enumerate(VARIANTS):
            seed_base = 60_000_000 + profile_index * 3_000_000 + variant_index * 1_000_000
            rows.extend(
                run_unconditioned_attempt_benchmark(
                    repo_root=repo_root,
                    profile_name=profile,
                    repetitions=unconditioned_repetitions,
                    seed_base=seed_base,
                    distribution_variant=variant,
                )
            )
            rows.extend(
                run_retry_until_success_benchmark(
                    repo_root=repo_root,
                    profile_name=profile,
                    repetitions=retry_repetitions,
                    seed_base=seed_base + 400_000,
                    distribution_variant=variant,
                    max_attempts_per_repetition=retry_limit,
                )
            )
    append_rows(raw_output, rows, resume=args.resume)
    correctness = json.loads(
        (_resolve(repo_root, args.correctness_input)).read_text(encoding="utf-8")
    )
    summary_rows, payload = summarize(raw_output, cast(dict[str, object], correctness))
    summary_output = _resolve(repo_root, args.summary_output)
    json_output = _resolve(repo_root, args.json_output)
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(summary_output, summary_rows)
    json_output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"result": payload["result"], "raw": str(raw_output)}))
    return 0


def summarize(
    raw_path: Path,
    correctness: dict[str, object],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    with raw_path.open(encoding="utf-8", newline="") as handle:
        raw_rows = list(csv.DictReader(handle))
    probabilities = {
        (str(row["profile"]), str(row["distribution_variant"])): cast(
            float, row["honest_execution_acceptance_rate"]
        )
        for row in cast(list[dict[str, object]], correctness["matrix"])
    }
    groups: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in raw_rows:
        groups[
            (
                row["profile"],
                row["distribution_variant"],
                row["operation"],
                row["phase"],
            )
        ].append(row)
    summary_rows: list[dict[str, object]] = []
    for (profile, variant, operation, phase), rows in sorted(groups.items()):
        measured = [
            row
            for row in rows
            if row["actual_execution_attempted"].lower() == "true"
            and row["phase"] != "total_end_to_end"
        ]
        elapsed = [int(row["elapsed_ns"]) for row in measured]
        accepted = sum(row["attempt_accepted"].lower() == "true" for row in measured)
        probability = probabilities.get((profile, variant), 0.0)
        mean_attempt = statistics.fmean(elapsed) if elapsed else 0.0
        summary_rows.append(
            {
                "profile": profile,
                "distribution_variant": variant,
                "operation": operation,
                "phase": phase,
                "sampling_condition": rows[0]["sampling_condition"],
                "measured_rows": len(measured),
                "accepted_rows": accepted,
                "rejected_rows": len(measured) - accepted,
                "acceptance_probability_from_unconditioned_matrix": probability,
                "mean_attempts_per_success": ("" if probability == 0.0 else 1.0 / probability),
                "mean_attempt_latency_ns": mean_attempt,
                "expected_time_per_success_ns": (
                    "" if probability == 0.0 else mean_attempt / probability
                ),
                "conditional_on_success": rows[0]["conditional_on_success"],
                "retry_time_included": rows[0]["retry_time_included"],
            }
        )
    payload = {
        "schema_version": 2,
        "result": "affected_benchmarks_complete_with_observed_correctness_failures",
        "distribution_variants": list(VARIANTS),
        "raw_path": str(raw_path),
        "legacy_reference_dataset": {
            "path": "artifacts/raw/LCLA_AKA/benchmark_raw.csv",
            "row_count": 49209,
            "distribution_variant": "legacy_reference",
            "sampling_condition": "conditional_success_path_latency_for_protocol_rows",
            "immutable": True,
        },
        "sampling_exact_reproduced": all(
            any(
                row["distribution_variant"] == variant
                and row["operation"] == operation
                and cast(int, row["measured_rows"]) >= 1000
                for row in summary_rows
            )
            for variant in VARIANTS
            for operation in SAMPLING_OPERATIONS
        ),
        "unconditioned_attempt_latency_present": any(
            row["operation"] == "unconditioned_attempt_latency" for row in summary_rows
        ),
        "retry_until_success_latency_present": any(
            row["operation"] == "retry_until_success_latency" for row in summary_rows
        ),
        "retry_time_included": all(
            cast(str, row["retry_time_included"]).lower() == "true"
            for row in summary_rows
            if row["operation"] == "retry_until_success_latency"
        ),
        "conditional_success_path_latency_is_not_table_v_equivalent": True,
        "summary": summary_rows,
    }
    return summary_rows, payload


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError("summary rows 不能为空")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


if __name__ == "__main__":
    raise SystemExit(main())
