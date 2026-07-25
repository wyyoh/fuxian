from __future__ import annotations

from scripts.reproduce_lcla_figure5 import build_figure5_data
from scripts.reproduce_lcla_figure6 import build_figure6_data


def test_figure5_lcla_has_three_rounds_and_seven_fields() -> None:
    rows, formulas = build_figure5_data()
    lcla = [row for row in rows if row["scheme"] == "LCLA-AKA"]

    assert {row["value"] for row in lcla if row["panel"] == "rounds"} == {3}
    assert {row["value"] for row in lcla if row["panel"] == "fields"} == {7}
    assert any(formula["status"] == "reconstructed_partial" for formula in formulas)


def test_figure6_example_order_is_verified_but_marked_partial() -> None:
    rows, formulas = build_figure6_data()
    example = [row for row in rows if row["entities"] == 50 and row["initiators"] == 100]

    other_rounds = {
        row["value"] for row in example if row["scheme"] != "LCLA-AKA" and row["panel"] == "rounds"
    }
    lcla_rounds = {
        row["value"] for row in example if row["scheme"] == "LCLA-AKA" and row["panel"] == "rounds"
    }
    other_fields = {
        row["value"] for row in example if row["scheme"] != "LCLA-AKA" and row["panel"] == "fields"
    }
    lcla_bits = {
        row["value"] for row in example if row["scheme"] == "LCLA-AKA" and row["panel"] == "bits"
    }
    assert other_rounds == {10_000}
    assert lcla_rounds == {400}
    assert other_fields == {5_000}
    assert lcla_bits == {10_000_000}
    assert all(
        "partial" in str(formula["status"]) or "conflicting" in str(formula["status"])
        for formula in formulas
    )
