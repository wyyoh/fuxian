#!/usr/bin/env python3
"""重构 LCLA-AKA Figure 6 多发起者三维源数据与投影图。"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from lattice_aka_repro.simple_png import render_line_panels

_FIELDS = (
    "panel",
    "scheme",
    "entities",
    "initiators",
    "value",
    "unit",
    "formula_id",
    "formula_variant",
    "status",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--data-output",
        type=Path,
        default=Path("artifacts/processed/LCLA_AKA/figure6_data.csv"),
    )
    parser.add_argument(
        "--formula-output",
        type=Path,
        default=Path("artifacts/processed/LCLA_AKA/figure6_formulas.json"),
    )
    parser.add_argument(
        "--figure-output",
        type=Path,
        default=Path("artifacts/figures/LCLA_AKA/figure6_reproduced.png"),
    )
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    rows, formulas = build_figure6_data()
    _write_csv(_resolve(repo_root, args.data_output), rows)
    formula_output = _resolve(repo_root, args.formula_output)
    formula_output.parent.mkdir(parents=True, exist_ok=True)
    formula_output.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "result": "figure6_partial_example_fitted_reconstruction",
                "formula_status": "partial",
                "paper_example": {
                    "entities": 50,
                    "initiators_interpreted_as": 100,
                    "other_rounds_order": 10_000,
                    "lcla_rounds_order": 400,
                    "other_fields_order": 5_000,
                    "lcla_fields_order": 400,
                    "other_bits_order": 100_000_000,
                    "lcla_bits_order": 10_000_000,
                },
                "formulas": formulas,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    render_line_panels(_panels_at_max_initiators(rows), _resolve(repo_root, args.figure_output))
    print(json.dumps({"result": "figure6_partial_reconstruction", "rows": len(rows)}))
    return 0


def build_figure6_data() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """生成 example-fitted 曲面；不把它冒充论文唯一公式。"""

    entities = (10, 20, 30, 40, 50)
    initiators = (20, 40, 60, 80, 100)
    schemes = ("Feng et al. [23]", "Dabra et al. [34]", "Ding et al. [35]", "LCLA-AKA")
    formulas: list[dict[str, object]] = [
        {
            "id": "F6-other-rounds",
            "formula": "2*entities*initiators",
            "source": "fitted to narrative maximum",
            "verified_example": "E=50,I=100 -> 10000",
            "ambiguity": "Figure 6 axis coordinates/formula are not tabulated",
            "status": "example_fitted_partial",
        },
        {
            "id": "F6-other-fields",
            "formula": "entities*initiators",
            "source": "fitted to narrative maximum",
            "verified_example": "E=50,I=100 -> 5000",
            "ambiguity": "conflicts with applying Figure 5's 3n+4/3n+5 per initiator",
            "status": "example_fitted_partial",
        },
        {
            "id": "F6-other-bits",
            "formula": "20000*entities*initiators",
            "source": "order-of-magnitude fit",
            "verified_example": "E=50,I=100 -> 1e8",
            "ambiguity": "paper gives only order of magnitude, not an exact coefficient",
            "status": "example_fitted_partial",
        },
        {
            "id": "F6-LCLA-rounds",
            "formula": "4*initiators",
            "source": "fitted to narrative maximum",
            "verified_example": "I=100 -> 400",
            "ambiguity": "conflicts with Figure 5's constant 3 rounds per initiator",
            "status": "example_fitted_conflicting",
        },
        {
            "id": "F6-LCLA-fields",
            "formula": "4*initiators",
            "source": "fitted to narrative maximum",
            "verified_example": "I=100 -> 400",
            "ambiguity": "conflicts with Figure 5's 7 transmitted fields per initiator",
            "status": "example_fitted_conflicting",
        },
        {
            "id": "F6-LCLA-bits",
            "formula": "100000*initiators",
            "source": "order-of-magnitude fit",
            "verified_example": "I=100 -> 1e7",
            "ambiguity": "conflicts with field-derived 3147008 bits per initiator",
            "status": "example_fitted_conflicting",
        },
    ]
    rows: list[dict[str, object]] = []
    for entity_count in entities:
        for initiator_count in initiators:
            for scheme in schemes:
                if scheme == "LCLA-AKA":
                    values = (
                        4 * initiator_count,
                        4 * initiator_count,
                        100_000 * initiator_count,
                    )
                    formula_ids = (
                        "F6-LCLA-rounds",
                        "F6-LCLA-fields",
                        "F6-LCLA-bits",
                    )
                    status = "example_fitted_conflicting"
                else:
                    values = (
                        2 * entity_count * initiator_count,
                        entity_count * initiator_count,
                        20_000 * entity_count * initiator_count,
                    )
                    formula_ids = (
                        "F6-other-rounds",
                        "F6-other-fields",
                        "F6-other-bits",
                    )
                    status = "example_fitted_partial"
                for panel, value, unit, formula_id in zip(
                    ("rounds", "fields", "bits"),
                    values,
                    ("rounds", "fields", "bits"),
                    formula_ids,
                    strict=True,
                ):
                    rows.append(
                        {
                            "panel": panel,
                            "scheme": scheme,
                            "entities": entity_count,
                            "initiators": initiator_count,
                            "value": value,
                            "unit": unit,
                            "formula_id": formula_id,
                            "formula_variant": "paper_narrative_example_fitted",
                            "status": status,
                        }
                    )
    return rows, formulas


def _panels_at_max_initiators(
    rows: list[dict[str, object]],
) -> list[dict[str, list[tuple[float, float]]]]:
    panels: list[dict[str, list[tuple[float, float]]]] = []
    for panel in ("rounds", "fields", "bits"):
        series: dict[str, list[tuple[float, float]]] = defaultdict(list)
        for row in rows:
            if row["panel"] == panel and row["initiators"] == 100:
                series[str(row["scheme"])].append(
                    (float(str(row["entities"])), float(str(row["value"])))
                )
        panels.append(series)
    return panels


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


if __name__ == "__main__":
    raise SystemExit(main())
