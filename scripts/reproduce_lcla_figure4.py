#!/usr/bin/env python3
"""由 Table V 分层结果重绘 LCLA-AKA Figure 4 reference curve。"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from itertools import pairwise
from pathlib import Path

from lattice_aka_repro.simple_png import render_line_panels

_DATA_FIELDS = (
    "series",
    "scheme",
    "profile",
    "evidence_class",
    "entities",
    "cost_ms",
    "formula",
    "formula_status",
)
_TREND_FIELDS = (
    "series",
    "completed_point_count",
    "spearman_rho",
    "monotonic_increasing",
    "trend_interpretation",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--table-input",
        type=Path,
        default=Path("artifacts/processed/LCLA_AKA/table_v_reproduced.csv"),
    )
    parser.add_argument(
        "--data-output",
        type=Path,
        default=Path("artifacts/processed/LCLA_AKA/figure4_data.csv"),
    )
    parser.add_argument(
        "--trend-output",
        type=Path,
        default=Path("artifacts/processed/LCLA_AKA/figure4_trend_summary.csv"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("artifacts/processed/LCLA_AKA/figure4_summary.json"),
    )
    parser.add_argument(
        "--figure-output",
        type=Path,
        default=Path("artifacts/figures/LCLA_AKA/figure4_reproduced.png"),
    )
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    rows = _read_csv(_resolve(repo_root, args.table_input))
    data = build_figure_data(rows)
    trends = build_trend_summary(data)
    _write_csv(_resolve(repo_root, args.data_output), data, _DATA_FIELDS)
    _write_csv(_resolve(repo_root, args.trend_output), trends, _TREND_FIELDS)
    series: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for row in data:
        series[str(row["series"])].append((float(str(row["entities"])), float(str(row["cost_ms"]))))
    render_line_panels([series], _resolve(repo_root, args.figure_output))
    payload = {
        "schema_version": 1,
        "result": "figure4_reconstructed_from_table_v_scaling",
        "strict_original_operation_timing_reproduced": False,
        "paper_frodo_native_curve_available": False,
        "numpy_reference_curve_available": any(
            row["evidence_class"] == "numpy_reference_reconstructed_from_operations" for row in data
        ),
        "audited_curve_available": any(str(row["profile"]).startswith("audited") for row in data),
        "formula_status": "reconstructed",
        "trend_point_minimum": 3,
        "spearman_interpretation": (
            "Spearman 只描述跨 entity 数量的秩趋势，不表示绝对计时严格复现。"
        ),
    }
    json_output = _resolve(repo_root, args.json_output)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"result": payload["result"], "series": len(series)}))
    return 0


def build_figure_data(table_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    entities = tuple(range(10, 101, 10))
    accepted_evidence = {
        "paper_reported_reference",
        "numpy_reference_reconstructed_from_operations",
    }
    for row in table_rows:
        if row["evidence_class"] not in accepted_evidence or not row["Sum_ms"]:
            continue
        series_name = (
            f"paper:{row['scheme']}"
            if row["evidence_class"] == "paper_reported_reference"
            else f"numpy:{row['profile']}"
        )
        per_entity_ms = float(row["Sum_ms"])
        for entity_count in entities:
            output.append(
                {
                    "series": series_name,
                    "scheme": row["scheme"],
                    "profile": row["profile"],
                    "evidence_class": row["evidence_class"],
                    "entities": entity_count,
                    "cost_ms": per_entity_ms * entity_count,
                    "formula": "entities * per_entity_Sum_ms",
                    "formula_status": "reconstructed",
                }
            )
    return output


def build_trend_summary(data: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in data:
        grouped[str(row["series"])].append(row)
    output: list[dict[str, object]] = []
    for series, rows in sorted(grouped.items()):
        ordered = sorted(rows, key=lambda row: int(str(row["entities"])))
        if len(ordered) < 3:
            output.append(
                {
                    "series": series,
                    "completed_point_count": len(ordered),
                    "spearman_rho": "",
                    "monotonic_increasing": "",
                    "trend_interpretation": "insufficient_completed_points",
                }
            )
            continue
        x_values = [float(str(row["entities"])) for row in ordered]
        y_values = [float(str(row["cost_ms"])) for row in ordered]
        rho = _spearman_rho(x_values, y_values)
        monotonic = all(left <= right for left, right in pairwise(y_values))
        output.append(
            {
                "series": series,
                "completed_point_count": len(ordered),
                "spearman_rho": rho,
                "monotonic_increasing": monotonic,
                "trend_interpretation": "rank_trend_only_not_absolute_timing_equivalence",
            }
        )
    return output


def _spearman_rho(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or len(left) < 3:
        raise ValueError("Spearman 至少需要三个成对点")
    left_ranks = _ranks(left)
    right_ranks = _ranks(right)
    count = len(left)
    squared = sum((a - b) ** 2 for a, b in zip(left_ranks, right_ranks, strict=True))
    return 1.0 - 6.0 * squared / (count * (count * count - 1))


def _ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        average = (start + 1 + end) / 2
        for index in order[start:end]:
            ranks[index] = average
        start = end
    return ranks


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


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
