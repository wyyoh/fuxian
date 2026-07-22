"""把当前运行环境写成 evidence schema JSON。"""

from __future__ import annotations

import argparse
from pathlib import Path

from lattice_aka_repro import collect_run_metadata, write_metadata_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--backend", required=True)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--warmup", required=True, type=int)
    parser.add_argument("--repetitions", required=True, type=int)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    metadata = collect_run_metadata(
        task_id=args.task_id,
        profile=args.profile,
        backend=args.backend,
        seed=args.seed,
        warmup=args.warmup,
        repetitions=args.repetitions,
        repo_root=args.repo_root,
    )
    output = write_metadata_json(metadata, args.output)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
