from __future__ import annotations

from pathlib import Path
from typing import cast

from lattice_aka_repro.lcla_backends import load_lcla_profile
from lattice_aka_repro.lcla_cost_model import build_cost_tables, communication_cost

_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_three_packets_and_seven_fields_are_distinct() -> None:
    payload = build_cost_tables(_REPO_ROOT)

    assert payload["network_rounds"] == 3
    assert payload["network_packets"] == 3
    assert payload["transmitted_fields"] == 7


def test_canonical_hash_encoding_is_not_wire_communication() -> None:
    profile = load_lcla_profile(_REPO_ROOT, "paper_performance")
    cost = communication_cost(profile, identity="爱丽丝@example.test")

    assert cost.canonical_hash_encoding_bytes > 0
    assert cost.network_wire_encoding_defined is False
    assert cost.paper_compact_message_bits != cost.canonical_hash_encoding_bytes * 8


def test_paper_compact_formula_is_derived_from_seven_fields() -> None:
    profile = load_lcla_profile(_REPO_ROOT, "toy")
    cost = communication_cost(profile)
    expected = 2 * profile.m * profile.m * profile.q.bit_length() + 5 * profile.m

    assert cost.paper_identity_bits == profile.m
    assert cost.paper_compact_message_bits == expected
    payload = build_cost_tables(_REPO_ROOT)
    rows = cast(list[dict[str, object]], payload["communication"])
    assert {row["profile"] for row in rows} == {
        "toy",
        "paper_correctness",
        "paper_performance",
        "audited_preserve_keylen",
        "audited_preserve_dimension",
    }
