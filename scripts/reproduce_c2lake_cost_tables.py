"""重算 C2LAKE 理论通信、存储和运算成本表。"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from lattice_aka_repro.c2lake_cost_model import (
    build_cost_tables,
    write_cost_csv,
    write_cost_json,
    write_cost_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("artifacts/processed/C2LAKE/cost_tables.json"),
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        default=Path("artifacts/processed/C2LAKE/cost_tables.csv"),
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        default=Path("reports/c2lake_cost_reproduction.md"),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_root = args.repo_root
    payload = build_cost_tables(specs_dir=repo_root / "specs")
    git_commit, git_dirty = _git_state(repo_root)
    payload["git_commit"] = git_commit
    payload["git_dirty"] = git_dirty
    write_cost_json(payload, args.json_output)
    write_cost_csv(payload, args.csv_output)
    write_cost_report(payload, args.report_output)
    print(args.json_output)
    print(args.csv_output)
    print(args.report_output)
    return 0 if payload["result"] == "pass" else 1


def _git_state(repo_root: Path) -> tuple[str, bool]:
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        text=True,
    ).strip()
    dirty = bool(
        subprocess.check_output(
            ["git", "status", "--porcelain=v1"],
            cwd=repo_root,
            text=True,
        ).strip()
    )
    return commit, dirty


if __name__ == "__main__":
    raise SystemExit(main())
