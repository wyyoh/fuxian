#!/usr/bin/env python3
"""重算 LCLA-AKA 通信、存储与运算成本。"""

from __future__ import annotations

import argparse
from pathlib import Path

from lattice_aka_repro.lcla_cost_model import build_cost_tables, write_cost_outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("artifacts/processed/LCLA_AKA/cost_tables.json"),
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        default=Path("artifacts/processed/LCLA_AKA/cost_tables.csv"),
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        default=Path("reports/lcla_aka_cost_reproduction.md"),
    )
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()

    def resolve(path: Path) -> Path:
        return path if path.is_absolute() else repo_root / path

    payload = build_cost_tables(repo_root)
    write_cost_outputs(
        payload,
        json_output=resolve(args.json_output),
        csv_output=resolve(args.csv_output),
        report_output=resolve(args.report_output),
    )
    print(
        f"{payload['result']}: rounds={payload['network_rounds']}, "
        f"packets={payload['network_packets']}, fields={payload['transmitted_fields']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
