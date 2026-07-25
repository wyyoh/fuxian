from __future__ import annotations

from pathlib import Path

from scripts.validate_lcla_full import public_packet_field_counts, validate_lcla_full

_ROOT = Path(__file__).resolve().parents[1]


def test_full_validation_keeps_partial_backend_and_formal_boundaries() -> None:
    payload = validate_lcla_full(repo_root=_ROOT, mode="smoke")

    assert payload["result"] == (
        "pass_with_partial_backend_and_partial_performance_unverified_formal_security"
    )
    assert payload["executable_validation_passed"] is True
    assert payload["protocol_correctness"] is True
    assert payload["failed_protocol_cases"] == 0
    assert payload["reconciliation_status"] is True
    assert payload["m1_consistency"] is True
    assert payload["m2_consistency"] is True
    assert payload["session_key_consistency"] is True
    assert payload["identity_recovery"] is True
    assert payload["formal_security_verified"] is False
    assert payload["mbr_formally_verified"] is False
    assert payload["quantum_security_verified"] is False
    assert payload["real_trapdoor_static_keygen_reproduced"] is False


def test_public_protocol_is_three_packets_and_seven_fields() -> None:
    assert public_packet_field_counts() == (3, 2, 2)
