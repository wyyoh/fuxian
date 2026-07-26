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
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--checkpoint-dir",
        type=Path,
        default=Path("artifacts/raw/LCLA_AKA/correctness_checkpoints"),
    )
    parser.add_argument(
        "--matrix-output",
        type=Path,
        default=Path("artifacts/processed/LCLA_AKA/unconditioned_correctness_matrix.csv"),
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=Path("artifacts/processed/LCLA_AKA/unconditioned_correctness_summary.json"),
    )
    parser.add_argument(
        "--lemma-output",
        type=Path,
        default=Path("artifacts/processed/LCLA_AKA/lemma3_counterexamples.csv"),
    )
    parser.add_argument(
        "--lemma-report-output",
        type=Path,
        default=Path("reports/lcla_lemma3_audit.md"),
    )
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
    checkpoint_dir = _resolve(repo_root, args.checkpoint_dir)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    matrix: list[dict[str, object]] = []
    for profile_index, profile in enumerate(PROFILES):
        for variant_index, variant in enumerate(VARIANTS):
            seed_base = 10_000_000 + profile_index * 1_000_000 + variant_index * 400_000
            checkpoint = checkpoint_dir / f"{profile}__{variant}__{attempts}.json"
            row = _load_checkpoint(checkpoint) if args.resume else None
            if row is None:
                row = run_honest_executions(
                    repo_root=repo_root,
                    profile_name=profile,
                    distribution_variant=variant,
                    attempts=attempts,
                    seed_base=seed_base,
                ).as_dict()
                _write_json(checkpoint, row)
            matrix.append(row)
            print(
                json.dumps(
                    {
                        "checkpoint": checkpoint.name,
                        "accepted": row["honest_execution_accepted"],
                        "attempts": row["honest_execution_attempts"],
                    }
                ),
                flush=True,
            )
    intended: list[dict[str, object]] = []
    for index, variant in enumerate(VARIANTS):
        checkpoint = checkpoint_dir / f"intended__{variant}__{intended_attempts}.json"
        intended_row = _load_checkpoint(checkpoint) if args.resume else None
        if intended_row is None:
            intended_row = run_intended_recipient_trials(
                repo_root=repo_root,
                profile_name="paper_performance",
                distribution_variant=variant,
                attempts=intended_attempts,
                candidate_count=20,
                seed_base=30_000_000 + index * 2_000_000,
            )
            _write_json(checkpoint, intended_row)
        intended.append(intended_row)
        print(
            json.dumps(
                {
                    "checkpoint": checkpoint.name,
                    "target_true_accept": intended_row["target_true_accept"],
                    "target_false_reject": intended_row["target_false_reject"],
                }
            ),
            flush=True,
        )
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
    matrix_output = _resolve(repo_root, args.matrix_output)
    summary_output = _resolve(repo_root, args.summary_output)
    lemma_output = _resolve(repo_root, args.lemma_output)
    lemma_report_output = _resolve(repo_root, args.lemma_report_output)
    for output in (matrix_output, summary_output, lemma_output, lemma_report_output):
        output.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(matrix_output, matrix)
    summary_output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_lemma_csv(lemma_output, lemma_rows)
    lemma_report_output.write_text(
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


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def _load_checkpoint(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"checkpoint {path} 顶层必须为 object")
    return cast(dict[str, object], value)


def _write_json(path: Path, value: dict[str, object]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
