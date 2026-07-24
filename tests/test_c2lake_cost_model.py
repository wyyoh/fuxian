from __future__ import annotations

from pathlib import Path
from typing import cast

from lattice_aka_repro.c2lake_cost_model import build_cost_tables

_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_cost_model_derives_c2lake_m32_communication_from_fields() -> None:
    payload = build_cost_tables(specs_dir=_REPO_ROOT / "specs")
    communication = cast(list[dict[str, object]], payload["communication"])
    paper_m32 = next(row for row in communication if row["profile"] == "paper_literal_m32")

    assert paper_m32["bits_per_zq"] == 10
    assert paper_m32["full_exchange_paper_bits"] == 2 * 6 * 640 * 10
    assert paper_m32["full_exchange_paper_bytes"] == 9_600
    serialized_bytes = paper_m32["full_exchange_serialized_bytes"]
    paper_bytes = paper_m32["full_exchange_paper_bytes"]
    assert isinstance(serialized_bytes, int)
    assert isinstance(paper_bytes, int)
    assert serialized_bytes > paper_bytes


def test_cost_model_sums_full_handshake_operation_counts() -> None:
    payload = build_cost_tables(specs_dir=_REPO_ROOT / "specs")
    operations = cast(list[dict[str, object]], payload["operations"])
    toy_rows = [row for row in operations if row["profile"] == "toy"]
    full = next(row for row in toy_rows if row["phase"] == "full_handshake")

    assert full["vector_times_matrix"] == sum(
        cast(int, row["vector_times_matrix"])
        for row in toy_rows
        if row["phase"] != "full_handshake"
    )
    assert full["matrix_times_vector"] == sum(
        cast(int, row["matrix_times_vector"])
        for row in toy_rows
        if row["phase"] != "full_handshake"
    )
    assert full["h3"] == 2
