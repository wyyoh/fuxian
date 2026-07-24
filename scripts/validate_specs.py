"""运行 T002 冻结规格机器校验。"""

from __future__ import annotations

import argparse
from pathlib import Path

from lattice_aka_repro.spec_validation import validate_specs, write_validation_outputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--specs-dir", type=Path)
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("artifacts/processed/T002/spec_validation.json"),
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        default=Path("reports/spec_validation.md"),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_root = args.repo_root
    specs_dir = args.specs_dir if args.specs_dir is not None else repo_root / "specs"
    result = validate_specs(specs_dir=specs_dir, repo_root=repo_root)
    json_output, report_output = write_validation_outputs(
        result,
        json_output=args.json_output,
        report_output=args.report_output,
    )
    print(json_output)
    print(report_output)
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
