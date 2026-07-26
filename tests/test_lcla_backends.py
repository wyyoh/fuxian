"""LCLA profile 与后端上下文负向测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from lattice_aka_repro.lcla_backends import load_lcla_profile, setup_lcla
from lattice_aka_repro.lcla_types import LCLAError, LCLAProfile

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "name",
    [
        "paper_correctness",
        "paper_performance",
        "audited_preserve_keylen",
        "audited_preserve_dimension",
        "toy",
    ],
)
def test_frozen_profiles_load(name: str) -> None:
    profile = load_lcla_profile(ROOT, name)
    assert profile.name == name
    assert profile.q % 2 == 1


def test_composite_literal_q_accepted_and_audited_prime_enforced() -> None:
    paper = load_lcla_profile(ROOT, "paper_performance")
    audited = load_lcla_profile(ROOT, "audited_preserve_dimension")
    assert paper.q == 16_777_215
    assert paper.q_must_be_prime is False
    assert audited.q == 16_777_259
    assert audited.q_must_be_prime is True


def test_invalid_profile_and_backend_rejected() -> None:
    with pytest.raises(LCLAError, match="PROFILE_ERROR"):
        load_lcla_profile(ROOT, "missing")
    with pytest.raises(LCLAError, match="PROFILE_ERROR"):
        LCLAProfile(
            name="bad",
            family="invalid",
            m=32,
            n=2,
            q=127,
            beta=1.0,
            q_must_be_prime=True,
        )
    profile = load_lcla_profile(ROOT, "toy")
    with pytest.raises(LCLAError, match="BACKEND_ERROR"):
        setup_lcla(
            profile=profile,
            backend="gpu",  # type: ignore[arg-type]
            keygen_backend="constructed_relation",
            seed=1,
        )
