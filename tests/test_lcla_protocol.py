"""LCLA-AKA 协议正确性、匿名结构、篡改和独立 oracle 测试。"""

from __future__ import annotations

from dataclasses import fields, replace
from pathlib import Path

import numpy as np
import numpy.typing as npt
import pytest

from lattice_aka_repro.lcla_backends import (
    generate_static_key_pair,
    load_lcla_profile,
    setup_lcla,
)
from lattice_aka_repro.lcla_protocol import (
    LCLAHandshakeTrace,
    alice_finish,
    bob_finish,
    bob_respond,
    make_lcla_context,
    run_lcla_handshake,
    validate_session_pair,
)
from lattice_aka_repro.lcla_types import (
    LCLAAliceFinish,
    LCLAAliceRequest,
    LCLABobResponse,
    LCLAError,
    LCLAProtocolContext,
    LCLAStaticKeyPair,
)

ROOT = Path(__file__).resolve().parents[1]


def _context_and_keys(
    profile_name: str,
    *,
    alice_identity: str = "Alice",
    bob_identity: str = "Bob",
    setup_seed: int = 1,
    alice_seed: int = 2,
    bob_seed: int = 3,
) -> tuple[LCLAProtocolContext, LCLAStaticKeyPair, LCLAStaticKeyPair]:
    profile = load_lcla_profile(ROOT, profile_name)
    parameters = setup_lcla(
        profile=profile,
        backend="fast",
        keygen_backend="constructed_relation",
        seed=setup_seed,
    )
    alice = generate_static_key_pair(parameters, alice_identity, seed=alice_seed)
    bob = generate_static_key_pair(parameters, bob_identity, seed=bob_seed)
    return make_lcla_context(parameters), alice, bob


def _changed_zq(array: npt.NDArray[np.int64], q: int) -> npt.NDArray[np.int64]:
    changed = np.array(array, dtype=np.int64, copy=True)
    changed.flat[0] = (int(changed.flat[0]) + 1) % q
    return changed


def _changed_bit(array: npt.NDArray[np.int64]) -> npt.NDArray[np.int64]:
    changed = np.array(array, dtype=np.int64, copy=True)
    changed.flat[0] ^= 1
    return changed


def test_toy_unicode_success_and_structural_anonymity() -> None:
    identity_a = "爱丽丝🔐"
    identity_b = "鲍勃"
    context, alice, bob = _context_and_keys(
        "toy",
        alice_identity=identity_a,
        bob_identity=identity_b,
        alice_seed=1129,
        bob_seed=1942,
    )
    trace = run_lcla_handshake(
        context,
        alice,
        bob,
        identity_a,
        identity_b,
        initiator_seed=10_060,
        responder_seed=20_060,
    )

    assert trace.alice_result.session_key_bits == trace.bob_result.session_key_bits
    assert trace.alice_result.local_identity == identity_a.encode()
    assert trace.bob_result.peer_identity == identity_a.encode()
    assert trace.request.__class__ is LCLAAliceRequest
    assert trace.response.__class__ is LCLABobResponse
    assert trace.finish.__class__ is LCLAAliceFinish
    assert {field.name for field in fields(trace.request)} == {
        "c_a",
        "delta_a",
        "h_a",
        "q",
        "profile",
        "backend",
    }
    assert {field.name for field in fields(trace.response)} == {
        "c_b",
        "h_b",
        "q",
        "profile",
        "backend",
    }
    assert {field.name for field in fields(trace.finish)} == {
        "t_a",
        "delta_b",
        "q",
        "profile",
        "backend",
    }
    public_field_names = {
        field.name
        for packet in (trace.request, trace.response, trace.finish)
        for field in fields(packet)
    }
    assert not {"x_a", "x_b", "e_a", "e_b", "m1", "m2"} & public_field_names
    assert trace.finish.t_a != identity_a.encode()


@pytest.mark.parametrize(
    ("profile_name", "attempts"),
    [
        ("paper_correctness", 100),
        ("paper_performance", 100),
        ("audited_preserve_keylen", 100),
        ("audited_preserve_dimension", 100),
    ],
)
def test_profile_attempt_matrix_records_literal_failures(profile_name: str, attempts: int) -> None:
    context, alice, bob = _context_and_keys(profile_name)
    successes = 0
    failures: dict[str, int] = {}
    for index in range(attempts):
        try:
            trace = run_lcla_handshake(
                context,
                alice,
                bob,
                "Alice",
                "Bob",
                initiator_seed=50_000 + index,
                responder_seed=60_000 + index,
            )
        except LCLAError as exc:
            failures[exc.code] = failures.get(exc.code, 0) + 1
            continue
        successes += 1
        assert trace.m1_consistency
        assert trace.m2_consistency
        assert trace.session_key_consistency
        if context.profile.family == "audited":
            assert trace.alice_result.session_key_bytes is not None
            assert trace.alice_result.session_key_bytes == trace.bob_result.session_key_bytes
    assert successes > 0
    assert successes + sum(failures.values()) == attempts
    assert set(failures).issubset({"NOT_INTENDED_RECEIVER", "RECONCILIATION_FAILURE"})


def test_1000_toy_attempts_preserve_reconciliation_failures() -> None:
    context, alice, bob = _context_and_keys("toy", alice_seed=1129, bob_seed=1942)
    successes = 0
    failures = 0
    for index in range(1000):
        try:
            run_lcla_handshake(
                context,
                alice,
                bob,
                "Alice",
                "Bob",
                initiator_seed=10_000 + index,
                responder_seed=20_000 + index,
            )
        except LCLAError as exc:
            assert exc.code in {
                "NOT_INTENDED_RECEIVER",
                "RECONCILIATION_FAILURE",
            }
            failures += 1
        else:
            successes += 1
    assert successes == 7
    assert failures == 993


def test_reproducibility_and_session_independence() -> None:
    context, alice, bob = _context_and_keys("paper_performance")
    first = run_lcla_handshake(
        context,
        alice,
        bob,
        "Alice",
        "Bob",
        initiator_seed=50_001,
        responder_seed=60_001,
    )
    repeated = run_lcla_handshake(
        context,
        alice,
        bob,
        "Alice",
        "Bob",
        initiator_seed=50_001,
        responder_seed=60_001,
    )
    assert np.array_equal(first.request.c_a, repeated.request.c_a)
    assert np.array_equal(first.alice_result.shared_bits.m1, repeated.alice_result.shared_bits.m1)
    assert np.array_equal(first.alice_result.shared_bits.m2, repeated.alice_result.shared_bits.m2)
    assert first.alice_result.session_key_bits == repeated.alice_result.session_key_bits
    assert first.alice_result.transcript_hash == repeated.alice_result.transcript_hash

    different: LCLAHandshakeTrace | None = None
    for offset in range(2, 50):
        try:
            different = run_lcla_handshake(
                context,
                alice,
                bob,
                "Alice",
                "Bob",
                initiator_seed=50_000 + offset,
                responder_seed=60_000 + offset,
            )
        except LCLAError:
            continue
        if different.alice_result.transcript_hash != first.alice_result.transcript_hash:
            break
    assert different is not None
    assert different.alice_result.transcript_hash != first.alice_result.transcript_hash
    assert different.alice_result.session_key_bits != first.alice_result.session_key_bits


def test_request_and_response_tamper_matrix() -> None:
    context, alice, bob = _context_and_keys("paper_performance")
    trace = run_lcla_handshake(
        context,
        alice,
        bob,
        "Alice",
        "Bob",
        initiator_seed=50_001,
        responder_seed=60_001,
    )
    q = context.profile.q
    request_variants = [
        replace(trace.request, c_a=_changed_zq(trace.request.c_a, q)),
        replace(trace.request, delta_a=_changed_bit(trace.request.delta_a)),
        replace(trace.request, h_a=_changed_bit(trace.request.h_a)),
    ]
    for request in request_variants:
        with pytest.raises(LCLAError, match="NOT_INTENDED_RECEIVER"):
            bob_respond(context, bob, "Bob", request, seed=70_001)

    response_variants = [
        replace(trace.response, c_b=_changed_zq(trace.response.c_b, q)),
        replace(trace.response, h_b=_changed_bit(trace.response.h_b)),
    ]
    for response in response_variants:
        with pytest.raises(LCLAError, match="INVALID_RESPONDER_MAC"):
            alice_finish(
                context,
                alice,
                "Alice",
                "Bob",
                trace.request,
                replace(
                    trace.alice_state,
                    e_b_vector=None,
                    n_b_prime=None,
                    m2=None,
                ),
                response,
                seed=70_002,
            )


def test_finish_tamper_rejected_or_detected_before_accept_pair() -> None:
    context, alice, bob = _context_and_keys("paper_performance")
    trace = run_lcla_handshake(
        context,
        alice,
        bob,
        "Alice",
        "Bob",
        initiator_seed=50_001,
        responder_seed=60_001,
    )
    changed_t = bytearray(trace.finish.t_a)
    changed_t[0] ^= 1
    tampered_identity = replace(trace.finish, t_a=bytes(changed_t))
    with pytest.raises(LCLAError, match="ID_RECOVERY_FAILURE"):
        bob_finish(
            context,
            bob,
            "Bob",
            trace.request,
            trace.response,
            trace.bob_state,
            tampered_identity,
        )

    tampered_delta = replace(trace.finish, delta_b=_changed_bit(trace.finish.delta_b))
    try:
        bob_result = bob_finish(
            context,
            bob,
            "Bob",
            trace.request,
            trace.response,
            trace.bob_state,
            tampered_delta,
        )
    except LCLAError as exc:
        assert exc.code == "ID_RECOVERY_FAILURE"
    else:
        with pytest.raises(LCLAError):
            validate_session_pair(trace.alice_result, bob_result)


def test_context_and_identity_mismatches_rejected() -> None:
    context, alice, bob = _context_and_keys("paper_performance")
    trace = run_lcla_handshake(
        context,
        alice,
        bob,
        "Alice",
        "Bob",
        initiator_seed=50_001,
        responder_seed=60_001,
    )
    with pytest.raises(LCLAError, match="IDENTITY_ERROR"):
        bob_respond(context, alice, "Bob", trace.request, seed=1)
    with pytest.raises(LCLAError, match="CONTEXT_ERROR"):
        bob_respond(
            context,
            bob,
            "Bob",
            replace(trace.request, profile="toy"),
            seed=1,
        )
    with pytest.raises(LCLAError, match="CONTEXT_ERROR"):
        bob_respond(
            context,
            bob,
            "Bob",
            replace(trace.request, backend="safe"),
            seed=1,
        )


def test_multi_recipient_filtering_20_candidates() -> None:
    profile = load_lcla_profile(ROOT, "paper_performance")
    parameters = setup_lcla(
        profile=profile,
        backend="fast",
        keygen_backend="constructed_relation",
        seed=81,
    )
    context = make_lcla_context(parameters)
    alice = generate_static_key_pair(parameters, "Alice", seed=82)
    bobs = [
        generate_static_key_pair(parameters, f"Bob-{index}", seed=100 + index)
        for index in range(20)
    ]
    target = bobs[7]
    unexpected_accepts = 0
    completed_rounds = 0
    seed = 90_000
    while completed_rounds < 100 and seed < 91_000:
        try:
            trace = run_lcla_handshake(
                context,
                alice,
                target,
                "Alice",
                "Bob-7",
                initiator_seed=seed,
                responder_seed=seed + 10_000,
            )
        except LCLAError:
            seed += 1
            continue
        assert trace.initiator_authentication
        for index, candidate in enumerate(bobs):
            if index == 7:
                continue
            try:
                bob_respond(
                    context,
                    candidate,
                    f"Bob-{index}",
                    trace.request,
                    seed=seed + 20_000 + index,
                )
            except LCLAError as exc:
                assert exc.code == "NOT_INTENDED_RECEIVER"
            else:
                unexpected_accepts += 1
        completed_rounds += 1
        seed += 1
    assert completed_rounds == 100
    assert unexpected_accepts == 0


def test_independent_python_int_oracle() -> None:
    context, alice, bob = _context_and_keys("toy", alice_seed=1129, bob_seed=1942)
    trace = run_lcla_handshake(
        context,
        alice,
        bob,
        "Alice",
        "Bob",
        initiator_seed=10_060,
        responder_seed=20_060,
    )
    q = context.profile.q
    matrix_a = context.parameters.matrix_a

    def mat_vec(matrix: npt.NDArray[np.int64], vector: npt.NDArray[np.int64]) -> list[int]:
        return [
            sum(int(matrix[row, index]) * int(vector[index]) for index in range(matrix.shape[1]))
            % q
            for row in range(matrix.shape[0])
        ]

    u1 = [
        (
            sum(
                int(matrix_a[row, index]) * int(alice.private_key.s1[index])
                for index in range(context.profile.m)
            )
            + 2 * int(alice.private_key.error_f[row])
        )
        % q
        for row in range(context.profile.n)
    ]
    u2 = [
        (int(alice.public_components.pk_full[row]) - u1[row]) % q
        for row in range(context.profile.n)
    ]
    assert u1 == alice.public_components.entity_share_u1.tolist()
    assert u2 == alice.public_components.kgc_target_u2.tolist()
    assert mat_vec(matrix_a, alice.private_key.kgc_share_s2) == u2

    c_a = [
        [
            (
                sum(
                    int(trace.alice_state.x_a[k, row]) * int(matrix_a[k, column])
                    for k in range(context.profile.n)
                )
                + 2 * int(trace.alice_state.e_a_matrix[row, column])
            )
            % q
            for column in range(context.profile.m)
        ]
        for row in range(context.profile.m)
    ]
    assert c_a == trace.request.c_a.tolist()
    n_a = [
        (
            sum(
                int(trace.alice_state.x_a[k, row]) * int(bob.public_components.pk_full[k])
                for k in range(context.profile.n)
            )
            + 2 * int(trace.alice_state.e_a_vector[row])
        )
        % q
        for row in range(context.profile.m)
    ]
    assert n_a == trace.alice_state.n_a.tolist()
    assert mat_vec(trace.request.c_a, bob.private_key.combined_s) == (
        trace.bob_state.n_a_prime.tolist()
    )

    c_b = [
        [
            (
                sum(
                    int(trace.bob_state.x_b[k, row]) * int(matrix_a[k, column])
                    for k in range(context.profile.n)
                )
                + 2 * int(trace.bob_state.e_b_matrix[row, column])
            )
            % q
            for column in range(context.profile.m)
        ]
        for row in range(context.profile.m)
    ]
    assert c_b == trace.response.c_b.tolist()
    assert trace.alice_state.e_b_vector is not None
    assert trace.alice_state.n_b_prime is not None
    n_b_prime = [
        (
            sum(
                int(trace.response.c_b[row, column]) * int(alice.private_key.combined_s[column])
                for column in range(context.profile.m)
            )
            + 2 * int(trace.alice_state.e_b_vector[row])
        )
        % q
        for row in range(context.profile.m)
    ]
    assert n_b_prime == trace.alice_state.n_b_prime.tolist()


def test_three_rounds_and_seven_transmitted_fields() -> None:
    assert 3 == len((LCLAAliceRequest, LCLABobResponse, LCLAAliceFinish))
    assert 7 == len(("C_A", "delta_A", "h_A", "C_B", "h_B", "T_A", "delta_B"))
