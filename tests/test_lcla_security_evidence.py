from __future__ import annotations

from pathlib import Path
from typing import cast

from scripts.audit_lcla_security_claims import audit

_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_security_audit_preserves_formal_verification_boundary() -> None:
    payload = audit(_REPO_ROOT)

    assert payload["result"] == "audit_complete_with_unverified_formal_security"
    assert payload["formal_security_verified"] is False
    assert payload["mbr_formally_verified"] is False
    assert payload["lwe_reduction_verified"] is False
    assert payload["isis_hardness_verified"] is False
    assert payload["anonymity_formally_verified"] is False
    assert payload["quantum_security_verified"] is False
    assert payload["paper_security_proof_reproduced"] is False


def test_constructed_backend_cannot_support_malicious_kgc_claim() -> None:
    payload = audit(_REPO_ROOT)
    claims = cast(list[dict[str, object]], payload["claims"])
    by_id = {str(claim["id"]): claim for claim in claims}

    assert by_id["malicious_KGC_resistance"]["status"] == "backend_not_reproduced"
    assert by_id["identity_anonymity"]["status"] == "structural_checked"
    assert by_id["quantum_security"]["status"] == "not_formally_verified"
    ambiguities = cast(list[dict[str, object]], payload["known_ambiguities"])
    assert {item["id"] for item in ambiguities} >= {"LCLA-D01", "LCLA-D11"}
