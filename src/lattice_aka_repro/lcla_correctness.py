"""LCLA-AKA 无条件正确性、目标接收者和 Lemma 3 审计工具。"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from lattice_aka_repro.lcla_backends import (
    generate_static_key_pair,
    load_lcla_profile,
    setup_lcla,
    verify_static_key,
)
from lattice_aka_repro.lcla_modular import matrix_vector_mod
from lattice_aka_repro.lcla_protocol import (
    alice_create_request,
    alice_finish,
    bob_finish,
    bob_respond,
    make_lcla_context,
)
from lattice_aka_repro.lcla_reconciliation import lemma3_error_bound, mod2, mu_0, mu_1
from lattice_aka_repro.lcla_types import DistributionVariant, LCLAError

CORRECTNESS_THRESHOLD = 0.999


@dataclass(frozen=True, slots=True)
class HonestExecutionSummary:
    """一个 profile/variant 的连续、无筛选执行统计。"""

    profile: str
    distribution_variant: DistributionVariant
    seed_start: int
    seed_end: int
    honest_execution_attempts: int
    honest_execution_accepted: int
    not_intended_receiver: int
    reconciliation_failure: int
    other_failure: int
    m1_mismatch: int
    m2_mismatch: int
    key_mismatch: int
    first_stage_false_reject_count: int
    final_reconciliation_failure_count: int
    static_relation_correctness: bool
    accepted_session_consistency: bool
    honest_execution_acceptance_rate: float
    wilson_95_low: float
    wilson_95_high: float
    paper_correctness_claim_reproduced: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def wilson_interval(
    successes: int, attempts: int, *, z: float = 1.959963984540054
) -> tuple[float, float]:
    """计算二项比例 Wilson 置信区间。"""

    if attempts <= 0 or successes < 0 or successes > attempts:
        raise ValueError("Wilson interval 需要 0<=successes<=attempts 且 attempts>0")
    proportion = successes / attempts
    denominator = 1.0 + z**2 / attempts
    center = (proportion + z**2 / (2.0 * attempts)) / denominator
    margin = (
        z
        * math.sqrt(proportion * (1.0 - proportion) / attempts + z**2 / (4.0 * attempts**2))
        / denominator
    )
    return max(0.0, center - margin), min(1.0, center + margin)


def paper_correctness_claim_reproduced(accepted: int, attempts: int) -> bool:
    """按冻结阈值判断，不允许由调用方降低标准。"""

    if attempts <= 0 or accepted < 0 or accepted > attempts:
        raise ValueError("需要 0<=accepted<=attempts 且 attempts>0")
    return accepted / attempts >= CORRECTNESS_THRESHOLD


def run_honest_executions(
    *,
    repo_root: Path,
    profile_name: str,
    distribution_variant: DistributionVariant,
    attempts: int,
    seed_base: int,
) -> HonestExecutionSummary:
    """按连续 seed 执行握手，不重试、不替换失败样本。"""

    if attempts <= 0:
        raise ValueError("attempts 必须为正")
    profile = load_lcla_profile(repo_root, profile_name)
    parameters = setup_lcla(
        profile=profile,
        backend="fast",
        keygen_backend="constructed_relation",
        seed=seed_base,
        distribution_variant=distribution_variant,
    )
    alice = generate_static_key_pair(parameters, "Alice", seed=seed_base + 1)
    bob = generate_static_key_pair(parameters, "Bob", seed=seed_base + 2)
    context = make_lcla_context(parameters)
    static_ok = verify_static_key(parameters, alice) and verify_static_key(parameters, bob)

    accepted = not_intended = reconciliation_failures = other_failures = 0
    m1_mismatches = m2_mismatches = key_mismatches = 0
    for index in range(attempts):
        initiator_seed = seed_base + 10_000 + index
        responder_seed = seed_base + 100_000 + index
        try:
            request, alice_state = alice_create_request(
                context,
                alice,
                "Alice",
                "Bob",
                seed=initiator_seed,
            )
            diagnostic_n_a_prime = matrix_vector_mod(
                request.c_a,
                bob.private_key.combined_s,
                q=profile.q,
                backend=context.backend,
            )
            diagnostic_m1_prime = mod2(diagnostic_n_a_prime, request.delta_a, q=profile.q)
            m1_matches = bool(np.array_equal(alice_state.m1, diagnostic_m1_prime))
            try:
                response, bob_state = bob_respond(
                    context,
                    bob,
                    "Bob",
                    request,
                    seed=responder_seed,
                )
            except LCLAError as exc:
                if exc.code == "NOT_INTENDED_RECEIVER":
                    not_intended += 1
                    if not m1_matches:
                        m1_mismatches += 1
                    continue
                raise
            finish, _, alice_result = alice_finish(
                context,
                alice,
                "Alice",
                "Bob",
                request,
                alice_state,
                response,
                seed=initiator_seed + 2_000_003,
            )
            bob_result = bob_finish(
                context,
                bob,
                "Bob",
                request,
                response,
                bob_state,
                finish,
            )
            m1_matches = bool(
                np.array_equal(alice_result.shared_bits.m1, bob_result.shared_bits.m1)
            )
            m2_matches = bool(
                np.array_equal(alice_result.shared_bits.m2, bob_result.shared_bits.m2)
            )
            key_matches = bool(
                alice_result.session_key_bits == bob_result.session_key_bits
                and alice_result.session_key_bytes == bob_result.session_key_bytes
            )
            if not m1_matches:
                m1_mismatches += 1
            if not m2_matches:
                m2_mismatches += 1
            if not key_matches:
                key_mismatches += 1
            if m1_matches and m2_matches and key_matches:
                accepted += 1
            else:
                reconciliation_failures += 1
        except LCLAError as exc:
            if exc.code in {"RECONCILIATION_FAILURE", "SESSION_KEY_MISMATCH"}:
                reconciliation_failures += 1
            elif exc.code == "NOT_INTENDED_RECEIVER":
                not_intended += 1
            else:
                other_failures += 1

    rate = accepted / attempts
    low, high = wilson_interval(accepted, attempts)
    return HonestExecutionSummary(
        profile=profile_name,
        distribution_variant=distribution_variant,
        seed_start=seed_base + 10_000,
        seed_end=seed_base + 10_000 + attempts - 1,
        honest_execution_attempts=attempts,
        honest_execution_accepted=accepted,
        not_intended_receiver=not_intended,
        reconciliation_failure=reconciliation_failures,
        other_failure=other_failures,
        m1_mismatch=m1_mismatches,
        m2_mismatch=m2_mismatches,
        key_mismatch=key_mismatches,
        first_stage_false_reject_count=not_intended,
        final_reconciliation_failure_count=reconciliation_failures,
        static_relation_correctness=static_ok,
        accepted_session_consistency=accepted > 0,
        honest_execution_acceptance_rate=rate,
        wilson_95_low=low,
        wilson_95_high=high,
        paper_correctness_claim_reproduced=paper_correctness_claim_reproduced(accepted, attempts),
    )


def run_intended_recipient_trials(
    *,
    repo_root: Path,
    profile_name: str,
    distribution_variant: DistributionVariant,
    attempts: int,
    candidate_count: int,
    seed_base: int,
) -> dict[str, object]:
    """让目标和全部非目标 Bob 处理每一个连续 seed 的 request。"""

    if attempts <= 0 or candidate_count < 2:
        raise ValueError("attempts 必须为正且 candidate_count>=2")
    profile = load_lcla_profile(repo_root, profile_name)
    parameters = setup_lcla(
        profile=profile,
        backend="fast",
        keygen_backend="constructed_relation",
        seed=seed_base,
        distribution_variant=distribution_variant,
    )
    context = make_lcla_context(parameters)
    alice = generate_static_key_pair(parameters, "Alice", seed=seed_base + 1)
    bobs = [
        generate_static_key_pair(parameters, f"Bob-{index}", seed=seed_base + 100 + index)
        for index in range(candidate_count)
    ]
    target_index = 7 if candidate_count > 7 else 0
    target_true_accept = target_false_reject = 0
    non_target_false_accept = non_target_true_reject = 0
    for index in range(attempts):
        request, _ = alice_create_request(
            context,
            alice,
            "Alice",
            f"Bob-{target_index}",
            seed=seed_base + 10_000 + index,
        )
        for bob_index, candidate in enumerate(bobs):
            try:
                bob_respond(
                    context,
                    candidate,
                    f"Bob-{bob_index}",
                    request,
                    seed=seed_base + 100_000 + index * candidate_count + bob_index,
                )
            except LCLAError as exc:
                if exc.code != "NOT_INTENDED_RECEIVER":
                    raise
                if bob_index == target_index:
                    target_false_reject += 1
                else:
                    non_target_true_reject += 1
            else:
                if bob_index == target_index:
                    target_true_accept += 1
                else:
                    non_target_false_accept += 1
    target_total = target_true_accept + target_false_reject
    non_target_total = non_target_false_accept + non_target_true_reject
    return {
        "profile": profile_name,
        "distribution_variant": distribution_variant,
        "candidate_count": candidate_count,
        "request_count": attempts,
        "seed_start": seed_base + 10_000,
        "seed_end": seed_base + 10_000 + attempts - 1,
        "seed_selection_used": False,
        "target_true_accept": target_true_accept,
        "target_false_reject": target_false_reject,
        "non_target_false_accept": non_target_false_accept,
        "non_target_true_reject": non_target_true_reject,
        "target_true_accept_rate": target_true_accept / target_total,
        "target_false_reject_rate": target_false_reject / target_total,
        "non_target_false_accept_rate": non_target_false_accept / non_target_total,
        "non_target_true_reject_rate": non_target_true_reject / non_target_total,
        "evidence_boundary": (
            "non_target_filtering_and_target_availability_statistics_not_anonymity_proof"
        ),
    }


def search_lemma3_counterexamples(q: int) -> dict[str, object]:
    """穷举小奇数 q 下论文 literal Definition 5/Lemma 3 条件。"""

    bound = lemma3_error_bound(q)
    errors = [error for error in range(-q, q + 1) if abs(error) < bound]
    violations = 0
    first: dict[str, object] | None = None
    for base in range(q):
        for error in errors:
            unwrapped_close = base + 2 * error
            close = unwrapped_close % q
            crossed = not 0 <= unwrapped_close < q
            for random_bit in (0, 1):
                delta = mu_0(close, q=q) if random_bit == 0 else mu_1(close, q=q)
                close_bit = int(
                    mod2(
                        np.asarray([close], dtype=np.int64),
                        np.asarray([delta], dtype=np.int64),
                        q=q,
                    )[0]
                )
                base_bit = int(
                    mod2(
                        np.asarray([base], dtype=np.int64),
                        np.asarray([delta], dtype=np.int64),
                        q=q,
                    )[0]
                )
                if close_bit == base_bit:
                    continue
                violations += 1
                if first is None:
                    first = {
                        "base": base,
                        "error": error,
                        "close_mod_q": close,
                        "random_bit": random_bit,
                        "delta": delta,
                        "base_bit": base_bit,
                        "close_bit": close_bit,
                        "error_bound_satisfied": abs(error) < bound,
                        "crossing_modular_boundary": crossed,
                    }
    return {
        "q": q,
        "q_is_prime": _is_prime(q),
        "error_bound": bound,
        "qualifying_error_count": len(errors),
        "violating_tuple_count": violations,
        "counterexample_found": first is not None,
        "first_counterexample": first,
    }


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2
    return True
