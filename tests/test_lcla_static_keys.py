"""LCLA-AKA constructed 静态密钥后端测试。"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import numpy.typing as npt
import pytest

from lattice_aka_repro.lcla_backends import (
    backend_capabilities,
    generate_static_key_pair,
    load_lcla_profile,
    setup_lcla,
    verify_static_key,
)
from lattice_aka_repro.lcla_types import LCLAError, LCLAStaticKeyPair

ROOT = Path(__file__).resolve().parents[1]


def _tamper(array: npt.NDArray[np.int64]) -> npt.NDArray[np.int64]:
    changed = np.array(array, dtype=np.int64, copy=True)
    changed.flat[0] = (int(changed.flat[0]) + 1) % 127
    return changed


def test_constructed_static_relation_1000_toy() -> None:
    profile = load_lcla_profile(ROOT, "toy")
    parameters = setup_lcla(
        profile=profile,
        backend="fast",
        keygen_backend="constructed_relation",
        seed=700,
    )
    for seed in range(1000):
        key_pair = generate_static_key_pair(parameters, f"toy-entity-{seed}", seed=10_000 + seed)
        assert verify_static_key(parameters, key_pair)
        assert key_pair.programmed_h1 is True
        assert key_pair.trapdoor_used is False
        assert key_pair.sample_pre_used is False


def test_constructed_static_relation_100_paper() -> None:
    profile = load_lcla_profile(ROOT, "paper_correctness")
    parameters = setup_lcla(
        profile=profile,
        backend="fast",
        keygen_backend="constructed_relation",
        seed=701,
    )
    for seed in range(100):
        key_pair = generate_static_key_pair(parameters, f"paper-entity-{seed}", seed=20_000 + seed)
        assert verify_static_key(parameters, key_pair)


def test_tampered_static_fields_and_identity_fail() -> None:
    profile = load_lcla_profile(ROOT, "toy")
    parameters = setup_lcla(
        profile=profile,
        backend="safe",
        keygen_backend="constructed_relation",
        seed=702,
    )
    key_pair = generate_static_key_pair(parameters, "alice", seed=703)
    public = key_pair.public_components
    private = key_pair.private_key

    variants = [
        replace(key_pair, private_key=replace(private, s1=_tamper(private.s1))),
        replace(
            key_pair,
            private_key=replace(private, kgc_share_s2=_tamper(private.kgc_share_s2)),
        ),
        replace(key_pair, private_key=replace(private, error_f=_tamper(private.error_f))),
        replace(
            key_pair,
            public_components=replace(public, entity_share_u1=_tamper(public.entity_share_u1)),
        ),
        replace(
            key_pair,
            public_components=replace(public, kgc_target_u2=_tamper(public.kgc_target_u2)),
        ),
        replace(
            key_pair,
            public_components=replace(public, pk_full=_tamper(public.pk_full)),
        ),
    ]
    assert all(not verify_static_key(parameters, variant) for variant in variants)
    assert not verify_static_key(parameters, key_pair, identity="mallory")


def test_programmed_h1_is_identity_bound_and_conflicts_rejected() -> None:
    profile = load_lcla_profile(ROOT, "toy")
    parameters = setup_lcla(
        profile=profile,
        backend="safe",
        keygen_backend="constructed_relation",
        seed=704,
    )
    first = generate_static_key_pair(parameters, "alice", seed=705)
    second = generate_static_key_pair(parameters, "bob", seed=706)
    assert not np.array_equal(first.public_components.pk_full, second.public_components.pk_full)
    with pytest.raises(LCLAError, match="H1_BINDING_ERROR"):
        generate_static_key_pair(parameters, "alice", seed=707)


def test_public_s2_is_not_combined_secret_or_entity_s1() -> None:
    profile = load_lcla_profile(ROOT, "toy")
    parameters = setup_lcla(
        profile=profile,
        backend="safe",
        keygen_backend="constructed_relation",
        seed=708,
    )
    key_pair = generate_static_key_pair(parameters, "alice", seed=709)
    private = key_pair.private_key
    assert not np.array_equal(private.kgc_share_s2, private.s1)
    assert not np.array_equal(private.kgc_share_s2, private.combined_s)


def test_backend_capabilities_and_real_backend_unavailable() -> None:
    constructed = backend_capabilities("constructed_relation")
    real = backend_capabilities("real_trapdoor")
    assert constructed.programmed_h1 is True
    assert constructed.real_trapdoor is False
    assert real.status == "unavailable"

    profile = load_lcla_profile(ROOT, "toy")
    with pytest.raises(LCLAError, match="BACKEND_UNAVAILABLE"):
        setup_lcla(
            profile=profile,
            backend="safe",
            keygen_backend="real_trapdoor",
            seed=710,
        )


def test_mixed_public_private_identity_rejected_by_type() -> None:
    profile = load_lcla_profile(ROOT, "toy")
    parameters = setup_lcla(
        profile=profile,
        backend="safe",
        keygen_backend="constructed_relation",
        seed=711,
    )
    alice = generate_static_key_pair(parameters, "alice", seed=712)
    bob = generate_static_key_pair(parameters, "bob", seed=713)
    with pytest.raises(LCLAError, match="IDENTITY_ERROR"):
        LCLAStaticKeyPair(
            public_components=alice.public_components,
            private_key=bob.private_key,
            programmed_h1=True,
            trapdoor_used=False,
            sample_pre_used=False,
        )
