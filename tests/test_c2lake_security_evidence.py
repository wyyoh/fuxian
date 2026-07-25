from __future__ import annotations

from pathlib import Path
from typing import cast

from scripts.audit_c2lake_security_claims import audit_security_claims
from scripts.validate_c2lake_full import validate_c2lake_full

_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_general_replay_resistance_is_not_executable_checked() -> None:
    payload = audit_security_claims(repo_root=_REPO_ROOT)
    claim_rows = cast(list[dict[str, object]], payload["claims"])
    claims = {claim["id"]: claim for claim in claim_rows}
    boundaries = cast(dict[str, object], payload["explicit_boundaries"])

    assert claims["timestamp_freshness_enforcement"]["status"] == "executable_checked"
    assert claims["expired_replay_rejection"]["status"] == "executable_checked"
    assert claims["general_replay_resistance"]["status"] == "paper_proof_only"
    assert claims["in_window_replay_prevention"]["implemented"] is False
    assert boundaries["in_window_replay_prevention"] is False
    assert boundaries["general_replay_resistance_executable_checked"] is False


def test_final_validation_result_names_partial_benchmark_and_unverified_security() -> None:
    payload = validate_c2lake_full(repo_root=_REPO_ROOT, mode="smoke")

    assert payload["result"] == "pass_with_partial_benchmark_and_unverified_formal_security"
    assert payload["executable_validation_passed"] is True
    assert payload["benchmark_status"] == "partial"
    assert payload["formal_security_verified"] is False
