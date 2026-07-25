from __future__ import annotations

from dataclasses import fields

import numpy as np
import numpy.typing as npt
import pytest

from lattice_aka_repro.c2lake_core import (
    C2LakeCoreError,
    C2LakeKeyPair,
    C2LakeMasterSecret,
    C2LakePublicParameters,
    centered_norm,
    extract_partial_private_key,
    set_secret_value,
    setup,
    verify_and_assemble_key,
)
from lattice_aka_repro.c2lake_protocol import (
    C2LakeRequest,
    C2LakeResponse,
    C2LakeTimestampPolicy,
    initiator_create_request,
    initiator_verify_and_finish,
    make_protocol_context,
    request_transcript_hash,
    responder_verify_and_reply,
    response_transcript_hash,
    run_handshake,
    verify_initiator_auth,
    verify_responder_auth,
)


def test_complete_handshake_correctness_for_required_profiles() -> None:
    cases = (
        ("toy", 1_000),
        ("paper_literal_m32", 100),
        ("audited_prime_m32", 100),
    )
    total_sessions = 0
    for profile, count in cases:
        public_params, alice_key_pair, bob_key_pair = _make_protocol_fixture(profile)
        alice_context = make_protocol_context(public_params, alice_key_pair, "alice@example.test")
        bob_context = make_protocol_context(public_params, bob_key_pair, "bob@example.test")
        policy = C2LakeTimestampPolicy(max_clock_skew=10, max_message_age=60)
        for offset in range(count):
            request, initiator_state = initiator_create_request(
                alice_context,
                bob_context.identity,
                timestamp=1_000,
                seed=10_000 + offset,
            )
            response, responder_state, bob_result = responder_verify_and_reply(
                bob_context,
                request,
                timestamp=1_001,
                seed=20_000 + offset,
                now=1_001,
                timestamp_policy=policy,
            )
            alice_result = initiator_verify_and_finish(
                alice_context,
                request,
                initiator_state,
                response,
                now=1_001,
                timestamp_policy=policy,
            )

            assert verify_initiator_auth(public_params, request)
            assert verify_responder_auth(public_params, response)
            assert alice_result.accepted
            assert bob_result.accepted
            assert alice_result.components.k1 == bob_result.components.k1
            assert alice_result.components.k2 == bob_result.components.k2
            assert alice_result.components.k3 == bob_result.components.k3
            assert alice_result.session_key_scalar == bob_result.session_key_scalar
            assert request_transcript_hash(request) == initiator_state.request_transcript_hash
            assert request_transcript_hash(request) == responder_state.request_transcript_hash
            assert response_transcript_hash(response) == responder_state.response_transcript_hash
            if public_params.family == "audited_prime":
                assert alice_result.session_key_bytes == bob_result.session_key_bytes
                assert alice_result.session_key_bytes is not None
                assert len(alice_result.session_key_bytes) == 32
            else:
                assert alice_result.session_key_bytes is None
                assert bob_result.session_key_bytes is None
            assert centered_norm(initiator_state.x_i, q=public_params.q) <= public_params.beta
            assert centered_norm(initiator_state.y_i, q=public_params.q) <= public_params.beta
            assert centered_norm(initiator_state.z_i, q=public_params.q) <= public_params.beta
            assert centered_norm(responder_state.x_j, q=public_params.q) <= public_params.beta
            assert centered_norm(responder_state.y_j, q=public_params.q) <= public_params.beta
            assert centered_norm(responder_state.z_j, q=public_params.q) <= public_params.beta
            assert _public_transcripts_do_not_expose_local_ephemeral_secrets()
            total_sessions += 1
    assert total_sessions == 1_200


def test_session_independence_and_reproducibility() -> None:
    public_params, alice_key_pair, bob_key_pair = _make_protocol_fixture("toy")
    policy = C2LakeTimestampPolicy(max_clock_skew=10, max_message_age=60)

    first_alice, first_bob = run_handshake(
        public_params,
        alice_key_pair,
        bob_key_pair,
        "alice@example.test",
        "bob@example.test",
        1_001,
        2_001,
        1_000,
        1_001,
        1_001,
        policy,
    )
    repeated_alice, repeated_bob = run_handshake(
        public_params,
        alice_key_pair,
        bob_key_pair,
        "alice@example.test",
        "bob@example.test",
        1_001,
        2_001,
        1_000,
        1_001,
        1_001,
        policy,
    )
    assert first_alice == repeated_alice
    assert first_bob == repeated_bob

    different_transcripts: set[str] = set()
    different_keys: set[int] = set()
    for offset in range(10):
        alice_result, _bob_result = run_handshake(
            public_params,
            alice_key_pair,
            bob_key_pair,
            "alice@example.test",
            "bob@example.test",
            3_000 + offset,
            4_000 + offset,
            1_000,
            1_001,
            1_001,
            policy,
        )
        different_transcripts.add(alice_result.transcript_hash)
        different_keys.add(alice_result.session_key_scalar)
    assert len(different_transcripts) > 1
    assert len(different_keys) > 1

    swapped_alice, _swapped_bob = run_handshake(
        public_params,
        bob_key_pair,
        alice_key_pair,
        "bob@example.test",
        "alice@example.test",
        1_001,
        2_001,
        1_000,
        1_001,
        1_001,
        policy,
    )
    assert swapped_alice.transcript_hash != first_alice.transcript_hash


@pytest.mark.parametrize("field_name", ["ID_i", "P_i0", "P_i1", "X_i", "Y_i", "Z_i", "S_i", "T_i"])
def test_tampered_initiator_request_is_rejected(field_name: str) -> None:
    public_params, alice_key_pair, bob_key_pair = _make_protocol_fixture("toy")
    alice_context = make_protocol_context(public_params, alice_key_pair, "alice@example.test")
    bob_context = make_protocol_context(public_params, bob_key_pair, "bob@example.test")
    request, _state = initiator_create_request(
        alice_context,
        bob_context.identity,
        timestamp=1_000,
        seed=11,
    )
    tampered = _tamper_request(request, field_name)

    with pytest.raises(C2LakeCoreError) as error_info:
        responder_verify_and_reply(
            bob_context,
            tampered,
            timestamp=1_001,
            seed=12,
            now=1_001,
            timestamp_policy=C2LakeTimestampPolicy(max_clock_skew=10, max_message_age=60),
        )
    assert error_info.value.code == "INVALID_INITIATOR_AUTH"


@pytest.mark.parametrize("field_name", ["ID_j", "P_j0", "P_j1", "X_j", "Y_j", "Z_j", "S_j", "T_j"])
def test_tampered_responder_response_is_rejected(field_name: str) -> None:
    public_params, alice_key_pair, bob_key_pair = _make_protocol_fixture("toy")
    alice_context = make_protocol_context(public_params, alice_key_pair, "alice@example.test")
    bob_context = make_protocol_context(public_params, bob_key_pair, "bob@example.test")
    policy = C2LakeTimestampPolicy(max_clock_skew=10, max_message_age=60)
    request, state = initiator_create_request(
        alice_context,
        bob_context.identity,
        timestamp=1_000,
        seed=21,
    )
    response, _responder_state, _bob_result = responder_verify_and_reply(
        bob_context,
        request,
        timestamp=1_001,
        seed=22,
        now=1_001,
        timestamp_policy=policy,
    )
    tampered = _tamper_response(response, field_name)

    with pytest.raises(C2LakeCoreError) as error_info:
        initiator_verify_and_finish(
            alice_context,
            request,
            state,
            tampered,
            now=1_001,
            timestamp_policy=policy,
        )
    assert error_info.value.code == "INVALID_RESPONDER_AUTH"


def test_timestamp_boundaries_and_replay_window() -> None:
    public_params, alice_key_pair, bob_key_pair = _make_protocol_fixture("toy")
    alice_context = make_protocol_context(public_params, alice_key_pair, "alice@example.test")
    bob_context = make_protocol_context(public_params, bob_key_pair, "bob@example.test")
    policy = C2LakeTimestampPolicy(max_clock_skew=10, max_message_age=100)

    for timestamp in (950, 900, 1_010):
        request, _state = initiator_create_request(
            alice_context,
            bob_context.identity,
            timestamp=timestamp,
            seed=100 + timestamp,
        )
        response, _responder_state, _bob_result = responder_verify_and_reply(
            bob_context,
            request,
            timestamp=1_000,
            seed=200 + timestamp,
            now=1_000,
            timestamp_policy=policy,
        )
        assert response.timestamp == 1_000

    for timestamp, expected_code in (
        (899, "MESSAGE_EXPIRED"),
        (1_011, "TIMESTAMP_IN_FUTURE"),
    ):
        request, _state = initiator_create_request(
            alice_context,
            bob_context.identity,
            timestamp=timestamp,
            seed=300 + timestamp,
        )
        with pytest.raises(C2LakeCoreError) as error_info:
            responder_verify_and_reply(
                bob_context,
                request,
                timestamp=1_000,
                seed=400 + timestamp,
                now=1_000,
                timestamp_policy=policy,
            )
        assert error_info.value.code == expected_code

    replayed_request, state = initiator_create_request(
        alice_context,
        bob_context.identity,
        timestamp=1_000,
        seed=501,
    )
    with pytest.raises(C2LakeCoreError) as request_replay_error:
        responder_verify_and_reply(
            bob_context,
            replayed_request,
            timestamp=1_000,
            seed=502,
            now=1_101,
            timestamp_policy=policy,
        )
    assert request_replay_error.value.code == "MESSAGE_EXPIRED"

    response, _responder_state, _bob_result = responder_verify_and_reply(
        bob_context,
        replayed_request,
        timestamp=1_000,
        seed=503,
        now=1_000,
        timestamp_policy=policy,
    )
    with pytest.raises(C2LakeCoreError) as response_replay_error:
        initiator_verify_and_finish(
            alice_context,
            replayed_request,
            state,
            response,
            now=1_101,
            timestamp_policy=policy,
        )
    assert response_replay_error.value.code == "MESSAGE_EXPIRED"


def test_in_window_replay_is_accepted_without_replay_cache() -> None:
    public_params, alice_key_pair, bob_key_pair = _make_protocol_fixture("toy")
    alice_context = make_protocol_context(public_params, alice_key_pair, "alice@example.test")
    bob_context = make_protocol_context(public_params, bob_key_pair, "bob@example.test")
    policy = C2LakeTimestampPolicy(max_clock_skew=10, max_message_age=100)
    request, _state = initiator_create_request(
        alice_context,
        bob_context.identity,
        timestamp=1_000,
        seed=551,
    )

    first_response, _first_state, first_result = responder_verify_and_reply(
        bob_context,
        request,
        timestamp=1_001,
        seed=552,
        now=1_001,
        timestamp_policy=policy,
    )
    second_response, _second_state, second_result = responder_verify_and_reply(
        bob_context,
        request,
        timestamp=1_002,
        seed=553,
        now=1_002,
        timestamp_policy=policy,
    )

    assert first_result.accepted
    assert second_result.accepted
    assert first_response.timestamp == 1_001
    assert second_response.timestamp == 1_002


def test_protocol_context_errors_are_reported_with_stable_codes() -> None:
    public_params, alice_key_pair, bob_key_pair = _make_protocol_fixture("toy")
    alice_context = make_protocol_context(public_params, alice_key_pair, "alice@example.test")
    bob_context = make_protocol_context(public_params, bob_key_pair, "bob@example.test")
    request, state = initiator_create_request(
        alice_context,
        bob_context.identity,
        timestamp=1_000,
        seed=600,
    )

    for tampered_request, expected_code in (
        (_replace_request(request, q=263), "MODULUS_ERROR"),
        (_replace_request(request, profile="other_profile"), "PROFILE_ERROR"),
        (_replace_request(request, backend="fast"), "BACKEND_ERROR"),
    ):
        with pytest.raises(C2LakeCoreError) as error_info:
            responder_verify_and_reply(
                bob_context,
                tampered_request,
                timestamp=1_001,
                seed=601,
                now=1_001,
                timestamp_policy=C2LakeTimestampPolicy(max_clock_skew=10, max_message_age=60),
            )
        assert error_info.value.code == expected_code

    with pytest.raises(C2LakeCoreError) as identity_error:
        make_protocol_context(public_params, alice_key_pair, "bob@example.test")
    assert identity_error.value.code == "IDENTITY_ERROR"

    with pytest.raises(C2LakeCoreError) as alice_uses_bob_key_error:
        make_protocol_context(public_params, bob_key_pair, "alice@example.test")
    assert alice_uses_bob_key_error.value.code == "IDENTITY_ERROR"

    with pytest.raises(C2LakeCoreError) as bob_uses_alice_key_error:
        make_protocol_context(public_params, alice_key_pair, "bob@example.test")
    assert bob_uses_alice_key_error.value.code == "IDENTITY_ERROR"

    mixed_public_key_request = _replace_request(request, p_i1=bob_key_pair.public_key.p_i1)
    with pytest.raises(C2LakeCoreError) as mixed_key_error:
        responder_verify_and_reply(
            bob_context,
            mixed_public_key_request,
            timestamp=1_001,
            seed=602,
            now=1_001,
            timestamp_policy=C2LakeTimestampPolicy(max_clock_skew=10, max_message_age=60),
        )
    assert mixed_key_error.value.code == "INVALID_INITIATOR_AUTH"

    response, _responder_state, _bob_result = responder_verify_and_reply(
        bob_context,
        request,
        timestamp=1_001,
        seed=603,
        now=1_001,
        timestamp_policy=C2LakeTimestampPolicy(max_clock_skew=10, max_message_age=60),
    )
    tampered_request = _tamper_request(request, "X_i")
    with pytest.raises(C2LakeCoreError) as state_error:
        initiator_verify_and_finish(
            alice_context,
            tampered_request,
            state,
            response,
            now=1_001,
            timestamp_policy=C2LakeTimestampPolicy(max_clock_skew=10, max_message_age=60),
        )
    assert state_error.value.code == "TRANSCRIPT_STATE_MISMATCH"


@pytest.mark.parametrize("profile", ["toy", "paper_literal_m32", "audited_prime_m32"])
def test_independent_python_int_protocol_oracle(profile: str) -> None:
    public_params, alice_key_pair, bob_key_pair = _make_protocol_fixture(profile)
    alice_context = make_protocol_context(public_params, alice_key_pair, "alice@example.test")
    bob_context = make_protocol_context(public_params, bob_key_pair, "bob@example.test")
    policy = C2LakeTimestampPolicy(max_clock_skew=10, max_message_age=60)
    request, initiator_state = initiator_create_request(
        alice_context,
        bob_context.identity,
        timestamp=1_000,
        seed=701,
    )
    response, responder_state, bob_result = responder_verify_and_reply(
        bob_context,
        request,
        timestamp=1_001,
        seed=702,
        now=1_001,
        timestamp_policy=policy,
    )
    alice_result = initiator_verify_and_finish(
        alice_context,
        request,
        initiator_state,
        response,
        now=1_001,
        timestamp_policy=policy,
    )

    _assert_independent_oracle(
        public_params,
        alice_key_pair,
        bob_key_pair,
        request,
        response,
        initiator_state.x_i,
        initiator_state.y_i,
        initiator_state.z_i,
        responder_state.x_j,
        responder_state.y_j,
        responder_state.z_j,
    )
    assert alice_result.components == bob_result.components
    assert alice_result.session_key_scalar == bob_result.session_key_scalar


def _make_protocol_fixture(
    profile: str,
) -> tuple[C2LakePublicParameters, C2LakeKeyPair, C2LakeKeyPair]:
    public_params, master_secret = setup(profile, seed=1_000, backend="safe")
    alice_key_pair = _make_key_pair(
        public_params,
        master_secret,
        "alice@example.test",
        secret_seed=1_001,
        partial_seed=1_002,
    )
    bob_key_pair = _make_key_pair(
        public_params,
        master_secret,
        "bob@example.test",
        secret_seed=1_003,
        partial_seed=1_004,
    )
    return public_params, alice_key_pair, bob_key_pair


def _make_key_pair(
    public_params: C2LakePublicParameters,
    master_secret: C2LakeMasterSecret,
    identity: str,
    *,
    secret_seed: int,
    partial_seed: int,
) -> C2LakeKeyPair:
    user_secret = set_secret_value(public_params, identity, seed=secret_seed)
    partial_key = extract_partial_private_key(
        public_params,
        master_secret,
        identity,
        user_secret.p_i1,
        seed=partial_seed,
    )
    return verify_and_assemble_key(public_params, identity, user_secret, partial_key)


def _public_transcripts_do_not_expose_local_ephemeral_secrets() -> bool:
    request_fields = {field.name for field in fields(C2LakeRequest)}
    response_fields = {field.name for field in fields(C2LakeResponse)}
    return not {"x_i", "y_i", "z_i"}.intersection(request_fields) and not {
        "x_j",
        "y_j",
        "z_j",
    }.intersection(response_fields)


def _tamper_request(request: C2LakeRequest, field_name: str) -> C2LakeRequest:
    if field_name == "ID_i":
        return _replace_request(request, identity=b"mallory@example.test")
    if field_name == "P_i0":
        return _replace_request(request, p_i0=_tamper_vector(request.p_i0, request.q))
    if field_name == "P_i1":
        return _replace_request(request, p_i1=_tamper_vector(request.p_i1, request.q))
    if field_name == "X_i":
        return _replace_request(request, x_i_public=_tamper_vector(request.x_i_public, request.q))
    if field_name == "Y_i":
        return _replace_request(request, y_i_public=_tamper_vector(request.y_i_public, request.q))
    if field_name == "Z_i":
        return _replace_request(request, z_i_public=_tamper_vector(request.z_i_public, request.q))
    if field_name == "S_i":
        return _replace_request(request, s_i=_tamper_vector(request.s_i, request.q))
    if field_name == "T_i":
        return _replace_request(request, timestamp=request.timestamp + 1)
    raise AssertionError(f"unexpected request field: {field_name}")


def _tamper_response(response: C2LakeResponse, field_name: str) -> C2LakeResponse:
    if field_name == "ID_j":
        return _replace_response(response, identity=b"mallory@example.test")
    if field_name == "P_j0":
        return _replace_response(response, p_j0=_tamper_vector(response.p_j0, response.q))
    if field_name == "P_j1":
        return _replace_response(response, p_j1=_tamper_vector(response.p_j1, response.q))
    if field_name == "X_j":
        return _replace_response(
            response, x_j_public=_tamper_vector(response.x_j_public, response.q)
        )
    if field_name == "Y_j":
        return _replace_response(
            response, y_j_public=_tamper_vector(response.y_j_public, response.q)
        )
    if field_name == "Z_j":
        return _replace_response(
            response, z_j_public=_tamper_vector(response.z_j_public, response.q)
        )
    if field_name == "S_j":
        return _replace_response(response, s_j=_tamper_vector(response.s_j, response.q))
    if field_name == "T_j":
        return _replace_response(response, timestamp=response.timestamp + 1)
    raise AssertionError(f"unexpected response field: {field_name}")


def _replace_request(request: C2LakeRequest, **overrides: object) -> C2LakeRequest:
    values = {
        "identity": request.identity,
        "q": request.q,
        "profile": request.profile,
        "backend": request.backend,
        "n": request.n,
        "p_i0": request.p_i0,
        "p_i1": request.p_i1,
        "x_i_public": request.x_i_public,
        "y_i_public": request.y_i_public,
        "z_i_public": request.z_i_public,
        "s_i": request.s_i,
        "timestamp": request.timestamp,
    }
    values.update(overrides)
    return C2LakeRequest(**values)  # type: ignore[arg-type]


def _replace_response(response: C2LakeResponse, **overrides: object) -> C2LakeResponse:
    values = {
        "identity": response.identity,
        "q": response.q,
        "profile": response.profile,
        "backend": response.backend,
        "n": response.n,
        "p_j0": response.p_j0,
        "p_j1": response.p_j1,
        "x_j_public": response.x_j_public,
        "y_j_public": response.y_j_public,
        "z_j_public": response.z_j_public,
        "s_j": response.s_j,
        "timestamp": response.timestamp,
    }
    values.update(overrides)
    return C2LakeResponse(**values)  # type: ignore[arg-type]


def _tamper_vector(vector: npt.NDArray[np.int64], q: int) -> npt.NDArray[np.int64]:
    tampered = vector.copy()
    tampered[0] = (int(tampered[0]) + 1) % q
    return tampered


def _assert_independent_oracle(
    public_params: C2LakePublicParameters,
    alice_key_pair: C2LakeKeyPair,
    bob_key_pair: C2LakeKeyPair,
    request: C2LakeRequest,
    response: C2LakeResponse,
    x_i: npt.NDArray[np.int64],
    y_i: npt.NDArray[np.int64],
    z_i: npt.NDArray[np.int64],
    x_j: npt.NDArray[np.int64],
    y_j: npt.NDArray[np.int64],
    z_j: npt.NDArray[np.int64],
) -> None:
    q = public_params.q
    matrix = public_params.matrix

    assert _python_vector_times_matrix(x_i, matrix, q) == request.x_i_public.tolist()
    assert _python_matrix_times_vector(matrix, y_i, q) == request.y_i_public.tolist()
    assert _python_matrix_times_vector(matrix, z_i, q) == request.z_i_public.tolist()
    assert _python_vector_times_matrix(x_j, matrix, q) == response.x_j_public.tolist()
    assert _python_matrix_times_vector(matrix, y_j, q) == response.y_j_public.tolist()
    assert _python_matrix_times_vector(matrix, z_j, q) == response.z_j_public.tolist()

    h1_i = public_params.hash_suite.h1(
        request.identity,
        request.p_i0,
        request.p_i1,
        public_params.public_key,
        q=q,
    )
    h2_i = public_params.hash_suite.h2(
        request.identity,
        request.p_i0,
        request.p_i1,
        request.x_i_public,
        request.y_i_public,
        request.z_i_public,
        request.timestamp,
        q=q,
    )
    h1_j = public_params.hash_suite.h1(
        response.identity,
        response.p_j0,
        response.p_j1,
        public_params.public_key,
        q=q,
    )
    h2_j = public_params.hash_suite.h2(
        response.identity,
        response.p_j0,
        response.p_j1,
        response.x_j_public,
        response.y_j_public,
        response.z_j_public,
        response.timestamp,
        q=q,
    )
    initiator_static = _python_zq_add(
        _python_zq_add(request.p_i0.tolist(), request.p_i1.tolist(), q),
        _python_zq_scalar_mul(h1_i, public_params.public_key.tolist(), q),
        q,
    )
    responder_static = _python_zq_add(
        _python_zq_add(response.p_j0.tolist(), response.p_j1.tolist(), q),
        _python_zq_scalar_mul(h1_j, public_params.public_key.tolist(), q),
        q,
    )
    expected_s_i_lhs = _python_vector_times_matrix(request.s_i, matrix, q)
    expected_s_i_rhs = _python_zq_add(
        request.x_i_public.tolist(),
        _python_zq_scalar_mul(h2_i, initiator_static, q),
        q,
    )
    expected_s_j_lhs = _python_vector_times_matrix(response.s_j, matrix, q)
    expected_s_j_rhs = _python_zq_add(
        response.x_j_public.tolist(),
        _python_zq_scalar_mul(h2_j, responder_static, q),
        q,
    )
    assert expected_s_i_lhs == expected_s_i_rhs
    assert expected_s_j_lhs == expected_s_j_rhs

    responder_private_sum = _python_zq_add(
        bob_key_pair.private_key.d_i0.tolist(),
        bob_key_pair.private_key.d_i1.tolist(),
        q,
    )
    initiator_private_sum = _python_zq_add(
        alice_key_pair.private_key.d_i0.tolist(),
        alice_key_pair.private_key.d_i1.tolist(),
        q,
    )
    bob_k1 = _python_dot(request.x_i_public.tolist(), y_j.tolist(), q)
    bob_k2 = _python_dot(x_j.tolist(), request.y_i_public.tolist(), q)
    bob_k3 = (
        _python_dot(initiator_static, z_j.tolist(), q)
        + _python_dot(responder_private_sum, request.z_i_public.tolist(), q)
    ) % q
    alice_k1 = _python_dot(x_i.tolist(), response.y_j_public.tolist(), q)
    alice_k2 = _python_dot(response.x_j_public.tolist(), y_i.tolist(), q)
    alice_k3 = (
        _python_dot(responder_static, z_i.tolist(), q)
        + _python_dot(initiator_private_sum, response.z_j_public.tolist(), q)
    ) % q
    assert alice_k1 == bob_k1
    assert alice_k2 == bob_k2
    assert alice_k3 == bob_k3


def _python_vector_times_matrix(
    vector: npt.NDArray[np.int64],
    matrix: npt.NDArray[np.int64],
    q: int,
) -> list[int]:
    return [
        sum(int(vector[row]) * int(matrix[row, column]) for row in range(vector.shape[0])) % q
        for column in range(matrix.shape[1])
    ]


def _python_matrix_times_vector(
    matrix: npt.NDArray[np.int64],
    vector: npt.NDArray[np.int64],
    q: int,
) -> list[int]:
    return [
        sum(int(matrix[row, column]) * int(vector[column]) for column in range(vector.shape[0])) % q
        for row in range(matrix.shape[0])
    ]


def _python_zq_add(left: list[int], right: list[int], q: int) -> list[int]:
    return [(left[index] + right[index]) % q for index in range(len(left))]


def _python_zq_scalar_mul(scalar: int, vector: list[int], q: int) -> list[int]:
    return [(scalar * value) % q for value in vector]


def _python_dot(left: list[int], right: list[int], q: int) -> int:
    return sum(int(left[index]) * int(right[index]) for index in range(len(left))) % q
