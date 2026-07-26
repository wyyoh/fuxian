"""LCLA-AKA 分布、无条件执行和 Lemma 3 正确性测试。"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import numpy as np

from lattice_aka_repro.lcla_backends import (
    generate_static_key_pair,
    load_lcla_profile,
    setup_lcla,
)
from lattice_aka_repro.lcla_correctness import (
    CORRECTNESS_THRESHOLD,
    paper_correctness_claim_reproduced,
    run_intended_recipient_trials,
    search_lemma3_counterexamples,
)
from lattice_aka_repro.lcla_gaussian import DiscreteGaussianSampler
from lattice_aka_repro.lcla_modular import centered_representative
from lattice_aka_repro.lcla_protocol import make_lcla_context, run_lcla_handshake

ROOT = Path(__file__).resolve().parents[1]


def test_paper_literal_s1_is_uniform_zq_not_gaussian() -> None:
    profile = load_lcla_profile(ROOT, "toy")
    parameters = setup_lcla(
        profile=profile,
        backend="fast",
        keygen_backend="constructed_relation",
        seed=7,
        distribution_variant="paper_literal_distribution",
    )
    key_pair = generate_static_key_pair(parameters, "Alice", seed=11)
    expected = np.random.Generator(np.random.PCG64(11)).integers(
        0, profile.q, size=profile.m, dtype=np.int64
    )

    assert np.array_equal(key_pair.private_key.s1, expected)
    assert np.max(np.abs(centered_representative(key_pair.private_key.s1, q=profile.q))) > 10
    assert key_pair.distribution_variant == "paper_literal_distribution"


def test_paper_and_standard_gaussian_exponents_are_distinct() -> None:
    paper = DiscreteGaussianSampler(
        beta=3.192,
        seed=19,
        exponent_variant="paper_definition3",
    ).sample((10_000,))
    standard = DiscreteGaussianSampler(
        beta=3.192,
        seed=19,
        exponent_variant="standard_lattice",
    ).sample((10_000,))

    assert paper.sampler_family != standard.sampler_family
    assert paper.tail_cutoff > standard.tail_cutoff
    assert not np.array_equal(paper.centered, standard.centered)
    assert float(np.var(paper.centered)) > float(np.var(standard.centered))


def test_distribution_variant_is_carried_by_key_and_trace() -> None:
    profile = load_lcla_profile(ROOT, "paper_performance")
    parameters = setup_lcla(
        profile=profile,
        backend="fast",
        keygen_backend="constructed_relation",
        seed=1,
        distribution_variant="proof_consistent_small_secret",
    )
    alice = generate_static_key_pair(parameters, "Alice", seed=2)
    bob = generate_static_key_pair(parameters, "Bob", seed=3)
    trace = run_lcla_handshake(
        make_lcla_context(parameters),
        alice,
        bob,
        "Alice",
        "Bob",
        initiator_seed=50_000,
        responder_seed=60_000,
    )

    assert alice.distribution_variant == "proof_consistent_small_secret"
    assert trace.distribution_variant == "proof_consistent_small_secret"


def test_correctness_threshold_is_frozen_at_0999() -> None:
    assert CORRECTNESS_THRESHOLD == 0.999
    assert paper_correctness_claim_reproduced(998, 1000) is False
    assert paper_correctness_claim_reproduced(999, 1000) is True


def test_intended_recipient_trials_do_not_screen_seeds() -> None:
    evidence = run_intended_recipient_trials(
        repo_root=ROOT,
        profile_name="toy",
        distribution_variant="proof_consistent_small_secret",
        attempts=3,
        candidate_count=20,
        seed_base=88_000_000,
    )

    assert evidence["seed_selection_used"] is False
    assert evidence["request_count"] == 3
    assert (
        cast(int, evidence["target_true_accept"]) + cast(int, evidence["target_false_reject"]) == 3
    )
    assert (
        cast(int, evidence["non_target_false_accept"])
        + cast(int, evidence["non_target_true_reject"])
        == 3 * 19
    )


def test_prime_q_counterexample_disables_universal_lemma3_flag() -> None:
    evidence = search_lemma3_counterexamples(31)

    assert evidence["q_is_prime"] is True
    assert evidence["counterexample_found"] is True
    assert cast(int, evidence["violating_tuple_count"]) > 0
