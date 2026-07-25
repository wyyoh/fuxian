#!/usr/bin/env python3
"""重构 LCLA-AKA Figure 5 单发起者通信曲线。"""

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
    "value",
    "unit",
    "formula_id",
    "evidence_class",
    "status",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--data-output",
        type=Path,
        default=Path("artifacts/processed/LCLA_AKA/figure5_data.csv"),
    )
    parser.add_argument(
        "--formula-output",
        type=Path,
        default=Path("artifacts/processed/LCLA_AKA/figure5_formulas.json"),
    )
    parser.add_argument(
        "--figure-output",
        type=Path,
        default=Path("artifacts/figures/LCLA_AKA/figure5_reproduced.png"),
    )
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    rows, formulas = build_figure5_data()
    _write_csv(_resolve(repo_root, args.data_output), rows)
    formula_output = _resolve(repo_root, args.formula_output)
    formula_output.parent.mkdir(parents=True, exist_ok=True)
    formula_output.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "result": "figure5_reconstructed_with_explicit_formula_status",
                "network_rounds": 3,
                "network_packets": 3,
                "lcla_transmitted_fields": 7,
                "network_wire_encoding_defined": False,
                "formulas": formulas,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    panels = _panels(rows)
    render_line_panels(panels, _resolve(repo_root, args.figure_output))
    print(json.dumps({"result": "figure5_reconstructed", "rows": len(rows)}))
    return 0


def build_figure5_data() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """按论文明确公式与可审计重构公式生成单发起者数据。"""

    entities = tuple(range(2, 51, 2))
    lcla_bits = 3_147_008
    schemes = ("Feng et al. [23]", "Dabra et al. [34]", "Ding et al. [35]", "LCLA-AKA")
    formulas: list[dict[str, object]] = [
        {
            "id": "F5-LCLA-rounds",
            "metric": "rounds",
            "formula": "3",
            "source": "paper narrative printed p9223",
            "verified_example": "all entities -> 3",
            "ambiguity": "none for the stated single-initiator round count",
            "status": "paper_reported_reference",
        },
        {
            "id": "F5-LCLA-fields",
            "metric": "fields",
            "formula": "7",
            "source": "paper narrative printed p9223",
            "verified_example": "all entities -> 7 statistical fields",
            "ambiguity": (
                "paper calls them messages; this reproduction treats them as fields in 3 packets"
            ),
            "status": "paper_reported_reference_reinterpreted_fields",
        },
        {
            "id": "F5-LCLA-bits",
            "metric": "bits",
            "formula": "2*m^2*bitlen(q)+5*m with m=256,q=2^24-1",
            "source": "field-level reconstruction",
            "verified_example": lcla_bits,
            "ambiguity": "paper Figure 5 exact plotted coordinate is not tabulated",
            "status": "reconstructed",
        },
        {
            "id": "F5-other-rounds",
            "metric": "rounds",
            "formula": "entities+2",
            "source": "paper narrative printed p9221",
            "verified_example": "n+2 statement",
            "ambiguity": "paper's n/entity indexing convention is not defined in the figure text",
            "status": "reconstructed",
        },
        {
            "id": "F5-Feng-fields",
            "metric": "fields",
            "formula": "3*entities+4",
            "source": "paper narrative printed p9221",
            "verified_example": "explicit 3n+4 statement",
            "ambiguity": "called messages rather than typed fields",
            "status": "paper_reported_reference",
        },
        {
            "id": "F5-Dabra-Ding-fields",
            "metric": "fields",
            "formula": "3*entities+5",
            "source": "paper narrative printed p9221",
            "verified_example": "explicit 3n+5 statement",
            "ambiguity": "called messages rather than typed fields",
            "status": "paper_reported_reference",
        },
        {
            "id": "F5-other-bits",
            "metric": "bits",
            "formula": "sender_bits + (entities-1)*receiver_bits",
            "source": "two-entity bit totals and broadcast narrative printed p9223",
            "verified_example": "entities=2 reproduces 8448/13064/16672 bits",
            "ambiguity": (
                "paper does not uniquely state whether sender broadcast payload is counted "
                "once or per receiver"
            ),
            "status": "reconstructed_partial",
        },
    ]
    rows: list[dict[str, object]] = []
    payloads = {
        "Feng et al. [23]": (4_352, 4_096),
        "Dabra et al. [34]": (6_664, 6_400),
        "Ding et al. [35]": (8_464, 8_208),
    }
    for entity_count in entities:
        for scheme in schemes:
            if scheme == "LCLA-AKA":
                rounds, fields, bits = 3, 7, lcla_bits
                formula_ids = ("F5-LCLA-rounds", "F5-LCLA-fields", "F5-LCLA-bits")
                statuses = (
                    "paper_reported_reference",
                    "paper_reported_reference_reinterpreted_fields",
                    "reconstructed",
                )
            else:
                sender_bits, receiver_bits = payloads[scheme]
                rounds = entity_count + 2
                fields = 3 * entity_count + (4 if scheme.startswith("Feng") else 5)
                bits = sender_bits + (entity_count - 1) * receiver_bits
                formula_ids = (
                    "F5-other-rounds",
                    "F5-Feng-fields" if scheme.startswith("Feng") else "F5-Dabra-Ding-fields",
                    "F5-other-bits",
                )
                statuses = ("reconstructed", "paper_reported_reference", "reconstructed_partial")
            for panel, value, unit, formula_id, status in zip(
                ("rounds", "fields", "bits"),
                (rounds, fields, bits),
                ("rounds", "fields", "bits"),
                formula_ids,
                statuses,
                strict=True,
            ):
                rows.append(
                    {
                        "panel": panel,
                        "scheme": scheme,
                        "entities": entity_count,
                        "value": value,
                        "unit": unit,
                        "formula_id": formula_id,
                        "evidence_class": (
                            "lcla_derived" if scheme == "LCLA-AKA" else "paper_reported_reference"
                        ),
                        "status": status,
                    }
                )
    return rows, formulas


def _panels(rows: list[dict[str, object]]) -> list[dict[str, list[tuple[float, float]]]]:
    panels: list[dict[str, list[tuple[float, float]]]] = []
    for panel in ("rounds", "fields", "bits"):
        series: dict[str, list[tuple[float, float]]] = defaultdict(list)
        for row in rows:
            if row["panel"] == panel:
                series[str(row["scheme"])].append(
                    (float(str(row["entities"])), float(str(row["value"])))
                )
        panels.append(series)
    return panels


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


if __name__ == "__main__":
    raise SystemExit(main())
