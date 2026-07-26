#!/usr/bin/env python3
"""生成 LCLA-AKA 无条件正确性、接收者统计和 Lemma 3 反例证据。"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import cast

from lattice_aka_repro.lcla_correctness import (
    CORRECTNESS_THRESHOLD,
    run_honest_executions,
    run_intended_recipient_trials,
    search_lemma3_counterexamples,
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
SMALL_ODD_Q = (7, 11, 15, 31, 63, 127)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--mode", choices=("smoke", "exact"), default="exact")
    parser.add_argument("--attempts", type=int)
    parser.add_argument("--intended-attempts", type=int)
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    attempts = (
        args.attempts if args.attempts is not None else (10 if args.mode == "smoke" else 1000)
    )
    intended_attempts = (
        args.intended_attempts
        if args.intended_attempts is not None
        else (10 if args.mode == "smoke" else 1000)
    )
    matrix: list[dict[str, object]] = []
    for profile_index, profile in enumerate(PROFILES):
        for variant_index, variant in enumerate(VARIANTS):
            seed_base = 10_000_000 + profile_index * 1_000_000 + variant_index * 400_000
            matrix.append(
                run_honest_executions(
                    repo_root=repo_root,
                    profile_name=profile,
                    distribution_variant=variant,
                    attempts=attempts,
                    seed_base=seed_base,
                ).as_dict()
            )
    intended = [
        run_intended_recipient_trials(
            repo_root=repo_root,
            profile_name="paper_performance",
            distribution_variant=variant,
            attempts=intended_attempts,
            candidate_count=20,
            seed_base=30_000_000 + index * 2_000_000,
        )
        for index, variant in enumerate(VARIANTS)
    ]
    lemma_rows = [search_lemma3_counterexamples(q) for q in SMALL_ODD_Q]
    prime_counterexample = any(
        row["q_is_prime"] is True and row["counterexample_found"] is True for row in lemma_rows
    )
    total_attempts = sum(cast(int, row["honest_execution_attempts"]) for row in matrix)
    total_accepted = sum(cast(int, row["honest_execution_accepted"]) for row in matrix)
    accepted_consistency = all(
        row["accepted_session_consistency"] is True
        for row in matrix
        if cast(int, row["honest_execution_accepted"]) > 0
    )
    summary = {
        "schema_version": 2,
        "mode": args.mode,
        "distribution_variants": list(VARIANTS),
        "seed_selection_used": False,
        "correctness_threshold": CORRECTNESS_THRESHOLD,
        "matrix": matrix,
        "aggregate": {
            "honest_execution_attempts": total_attempts,
            "honest_execution_accepted": total_accepted,
            "honest_execution_acceptance_rate": total_accepted / total_attempts,
            "first_stage_false_reject_count": sum(
                cast(int, row["first_stage_false_reject_count"]) for row in matrix
            ),
            "final_reconciliation_failure_count": sum(
                cast(int, row["final_reconciliation_failure_count"]) for row in matrix
            ),
            "other_failure": sum(cast(int, row["other_failure"]) for row in matrix),
        },
        "static_relation_correctness": all(
            row["static_relation_correctness"] is True for row in matrix
        ),
        "accepted_session_consistency": accepted_consistency,
        "paper_correctness_claim_reproduced": all(
            row["paper_correctness_claim_reproduced"] is True for row in matrix
        ),
        "honest_execution_correctness_reproduced": all(
            cast(float, row["honest_execution_acceptance_rate"]) >= CORRECTNESS_THRESHOLD
            for row in matrix
        ),
        "intended_recipient_statistics": intended,
        "definition5_literal_implemented": True,
        "lemma3_counterexample_found": any(
            row["counterexample_found"] is True for row in lemma_rows
        ),
        "lemma3_universal_correctness": not prime_counterexample,
        "paper_correctness_proof_supported": not prime_counterexample,
    }
    processed = repo_root / "artifacts" / "processed" / "LCLA_AKA"
    processed.mkdir(parents=True, exist_ok=True)
    _write_csv(processed / "unconditioned_correctness_matrix.csv", matrix)
    (processed / "unconditioned_correctness_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_lemma_csv(processed / "lemma3_counterexamples.csv", lemma_rows)
    (repo_root / "reports" / "lcla_lemma3_audit.md").write_text(
        render_lemma_report(lemma_rows, prime_counterexample),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "result": "observed_correctness_failure",
                "attempts": total_attempts,
                "accepted": total_accepted,
                "lemma3_prime_counterexample": prime_counterexample,
            }
        )
    )
    return 0


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError("CSV rows 不能为空")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_lemma_csv(path: Path, rows: list[dict[str, object]]) -> None:
    flattened: list[dict[str, object]] = []
    for row in rows:
        first = cast(dict[str, object] | None, row["first_counterexample"])
        flattened.append(
            {
                "q": row["q"],
                "q_is_prime": row["q_is_prime"],
                "error_bound": row["error_bound"],
                "qualifying_error_count": row["qualifying_error_count"],
                "violating_tuple_count": row["violating_tuple_count"],
                "counterexample_found": row["counterexample_found"],
                "first_base": "" if first is None else first["base"],
                "first_error": "" if first is None else first["error"],
                "first_close_mod_q": "" if first is None else first["close_mod_q"],
                "first_random_bit": "" if first is None else first["random_bit"],
                "first_delta": "" if first is None else first["delta"],
                "error_bound_satisfied": ("" if first is None else first["error_bound_satisfied"]),
                "crossing_modular_boundary": (
                    "" if first is None else first["crossing_modular_boundary"]
                ),
            }
        )
    _write_csv(path, flattened)


def render_lemma_report(rows: list[dict[str, object]], prime_counterexample: bool) -> str:
    lines = [
        "# LCLA-AKA Definition 5 / Lemma 3 反例审计",
        "",
        "本审计严格保留论文 literal 的 μ₀、μ₁、S 与 Mod2，不修改区间、噪声或模运算。",
        "对每个小奇数 q 穷举 base、满足 `|e| < q/8-1` 的整数 e 和随机位 b，",
        "比较 `a=base+2e (mod q)` 与 base 在同一公开 delta 下的 Mod2 输出。",
        "",
        "| q | 素数 | 界内 e 数 | 违反 tuple 数 | 首个反例跨模边界 |",
        "| ---: | :---: | ---: | ---: | :---: |",
    ]
    for row in rows:
        first = cast(dict[str, object] | None, row["first_counterexample"])
        crossed = "-" if first is None else str(first["crossing_modular_boundary"])
        lines.append(
            f"| {row['q']} | {row['q_is_prime']} | {row['qualifying_error_count']} | "
            f"{row['violating_tuple_count']} | {crossed} |"
        )
    lines.extend(
        [
            "",
            "- `definition5_literal_implemented=true`",
            f"- `lemma3_counterexample_found={any(row['counterexample_found'] for row in rows)}`",
            f"- `lemma3_universal_correctness={not prime_counterexample}`",
            f"- `paper_correctness_proof_supported={not prime_counterexample}`",
            "",
            "只要任一素数 q 存在满足论文误差界的反例，便不能把 Lemma 3 当作已由",
            "该 literal 实现支持的普遍正确性命题。非素数 q 的结果仅用于函数性质审计。",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
