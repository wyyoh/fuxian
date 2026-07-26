"""LCLA-AKA 三轮、七字段匿名认证密钥协商参考实现。"""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from lattice_aka_repro.lcla_backends import verify_static_key
from lattice_aka_repro.lcla_gaussian import DiscreteGaussianSampler
from lattice_aka_repro.lcla_hashes import (
    normalize_identity,
    transcript_hash,
    xor_identity,
)
from lattice_aka_repro.lcla_modular import (
    map_centered_to_zq,
    matrix_add_mod,
    matrix_vector_mod,
    scalar_multiply_mod,
    transpose_matrix_matrix_mod,
    transpose_matrix_vector_mod,
    vector_add_mod,
)
from lattice_aka_repro.lcla_reconciliation import mod2, signal
from lattice_aka_repro.lcla_types import (
    IntArray,
    LCLAAliceEphemeralState,
    LCLAAliceFinish,
    LCLAAliceRequest,
    LCLABobEphemeralState,
    LCLABobResponse,
    LCLAError,
    LCLAParameters,
    LCLAProtocolContext,
    LCLASessionResult,
    LCLASharedBits,
    LCLAStaticKeyPair,
)


@dataclass(frozen=True, slots=True)
class LCLAHandshakeTrace:
    """完整握手结果及三轮公开 packet。"""

    request: LCLAAliceRequest
    response: LCLABobResponse
    finish: LCLAAliceFinish
    alice_state: LCLAAliceEphemeralState
    bob_state: LCLABobEphemeralState
    alice_result: LCLASessionResult
    bob_result: LCLASessionResult
    initiator_authentication: bool
    responder_authentication: bool
    m1_consistency: bool
    m2_consistency: bool
    session_key_consistency: bool
    distribution_variant: str


def make_lcla_context(parameters: LCLAParameters) -> LCLAProtocolContext:
    """从公共参数生成类型化协议上下文。"""

    return LCLAProtocolContext(
        parameters=parameters,
        hash_suite=parameters.hash_suite,
        profile=parameters.profile,
        backend=parameters.backend,
        keygen_backend=parameters.keygen_backend,
        distribution_variant=parameters.distribution_variant,
    )


def _check_key_context(
    context: LCLAProtocolContext,
    key_pair: LCLAStaticKeyPair,
    identity: str | bytes,
) -> bytes:
    identity_bytes = normalize_identity(identity)
    if key_pair.private_key.identity != identity_bytes:
        raise LCLAError("IDENTITY_ERROR", "identity 与 static key pair 不一致")
    if (
        key_pair.private_key.q != context.profile.q
        or key_pair.private_key.profile != context.profile.name
        or key_pair.private_key.backend != context.backend
        or key_pair.private_key.keygen_backend != context.keygen_backend
        or key_pair.distribution_variant != context.distribution_variant
    ):
        raise LCLAError("CONTEXT_ERROR", "static key pair 与协议上下文不一致")
    if not verify_static_key(context.parameters, key_pair, identity=identity_bytes):
        raise LCLAError("STATIC_KEY_VERIFY_ERROR", "static key relation 失败")
    return identity_bytes


def _check_packet_context(
    context: LCLAProtocolContext,
    *,
    q: int,
    profile: str,
    backend: str,
) -> None:
    if q != context.profile.q or profile != context.profile.name or backend != context.backend:
        raise LCLAError("CONTEXT_ERROR", "packet 与协议上下文不一致")


def _sample_ephemeral(
    context: LCLAProtocolContext,
    *,
    seed: int,
    include_vector: bool,
) -> tuple[IntArray, IntArray, IntArray | None]:
    profile = context.profile
    sampler = DiscreteGaussianSampler(
        beta=profile.beta,
        seed=seed,
        exponent_variant=(
            "paper_definition3"
            if context.distribution_variant == "paper_literal_distribution"
            else "standard_lattice"
        ),
    )
    matrix_x = map_centered_to_zq(sampler.sample((profile.n, profile.m)).centered, q=profile.q)
    matrix_e = map_centered_to_zq(sampler.sample((profile.m, profile.m)).centered, q=profile.q)
    vector_e = None
    if include_vector:
        vector_e = map_centered_to_zq(sampler.sample((profile.m,)).centered, q=profile.q)
    return matrix_x, matrix_e, vector_e


def alice_create_request(
    context: LCLAProtocolContext,
    alice_key_pair: LCLAStaticKeyPair,
    alice_identity: str | bytes,
    bob_identity: str | bytes,
    *,
    seed: int,
) -> tuple[LCLAAliceRequest, LCLAAliceEphemeralState]:
    """Alice 第一轮：生成 (C_A,delta_A,h_A)。"""

    identity_a = _check_key_context(context, alice_key_pair, alice_identity)
    del identity_a
    identity_b = normalize_identity(bob_identity)
    pk_b = context.hash_suite.h1(identity_b)
    x_a, e_a_matrix, sampled_e_a = _sample_ephemeral(context, seed=seed, include_vector=True)
    if sampled_e_a is None:  # pragma: no cover - include_vector 已固定为 True
        raise AssertionError("e_A vector missing")
    profile = context.profile
    c_a = matrix_add_mod(
        transpose_matrix_matrix_mod(
            x_a,
            context.parameters.matrix_a,
            q=profile.q,
            backend=context.backend,
        ),
        scalar_multiply_mod(2, e_a_matrix, q=profile.q),
        q=profile.q,
    )
    n_a = vector_add_mod(
        transpose_matrix_vector_mod(x_a, pk_b, q=profile.q, backend=context.backend),
        scalar_multiply_mod(2, sampled_e_a, q=profile.q),
        q=profile.q,
    )
    signal_a = signal(n_a, q=profile.q, seed=seed + 1_000_003)
    m1 = mod2(n_a, signal_a.delta, q=profile.q)
    h_a = context.hash_suite.mac_a(c_a, m1, signal_a.delta)
    request = LCLAAliceRequest(
        c_a=c_a,
        delta_a=signal_a.delta,
        h_a=h_a,
        q=profile.q,
        profile=profile.name,
        backend=context.backend,
    )
    state = LCLAAliceEphemeralState(
        x_a=x_a,
        e_a_matrix=e_a_matrix,
        e_a_vector=sampled_e_a,
        n_a=n_a,
        m1=m1,
        signal_random_bits_a=signal_a.random_bits,
        e_b_vector=None,
        n_b_prime=None,
        m2=None,
        q=profile.q,
        profile=profile.name,
        backend=context.backend,
        distribution_variant=context.distribution_variant,
    )
    return request, state


def bob_respond(
    context: LCLAProtocolContext,
    bob_key_pair: LCLAStaticKeyPair,
    bob_identity: str | bytes,
    request: LCLAAliceRequest,
    *,
    seed: int,
) -> tuple[LCLABobResponse, LCLABobEphemeralState]:
    """Bob 验证目标接收者 MAC，成功后生成第二轮。"""

    _check_key_context(context, bob_key_pair, bob_identity)
    _check_packet_context(
        context,
        q=request.q,
        profile=request.profile,
        backend=request.backend,
    )
    profile = context.profile
    n_a_prime = matrix_vector_mod(
        request.c_a,
        bob_key_pair.private_key.combined_s,
        q=profile.q,
        backend=context.backend,
    )
    m1_prime = mod2(n_a_prime, request.delta_a, q=profile.q)
    expected_h_a = context.hash_suite.mac_a(request.c_a, m1_prime, request.delta_a)
    if not np.array_equal(expected_h_a, request.h_a):
        raise LCLAError(
            "NOT_INTENDED_RECEIVER",
            "h_A 验证失败；不生成 Bob ephemeral state 或 session key",
        )
    x_b, e_b_matrix, _ = _sample_ephemeral(context, seed=seed, include_vector=False)
    c_b = matrix_add_mod(
        transpose_matrix_matrix_mod(
            x_b,
            context.parameters.matrix_a,
            q=profile.q,
            backend=context.backend,
        ),
        scalar_multiply_mod(2, e_b_matrix, q=profile.q),
        q=profile.q,
    )
    h_b = context.hash_suite.mac_b(c_b, m1_prime)
    response = LCLABobResponse(
        c_b=c_b,
        h_b=h_b,
        q=profile.q,
        profile=profile.name,
        backend=context.backend,
    )
    state = LCLABobEphemeralState(
        x_b=x_b,
        e_b_matrix=e_b_matrix,
        n_a_prime=n_a_prime,
        m1_prime=m1_prime,
        q=profile.q,
        profile=profile.name,
        backend=context.backend,
        distribution_variant=context.distribution_variant,
    )
    return response, state


def alice_finish(
    context: LCLAProtocolContext,
    alice_key_pair: LCLAStaticKeyPair,
    alice_identity: str | bytes,
    bob_identity: str | bytes,
    request: LCLAAliceRequest,
    alice_state: LCLAAliceEphemeralState,
    response: LCLABobResponse,
    *,
    seed: int,
) -> tuple[LCLAAliceFinish, LCLAAliceEphemeralState, LCLASessionResult]:
    """Alice 验证 h_B，生成身份掩码和第三轮。"""

    identity_a = _check_key_context(context, alice_key_pair, alice_identity)
    identity_b = normalize_identity(bob_identity)
    _check_packet_context(
        context,
        q=response.q,
        profile=response.profile,
        backend=response.backend,
    )
    if (
        alice_state.q != context.profile.q
        or alice_state.profile != context.profile.name
        or alice_state.backend != context.backend
        or alice_state.distribution_variant != context.distribution_variant
    ):
        raise LCLAError("CONTEXT_ERROR", "Alice ephemeral state 上下文不一致")
    expected_h_b = context.hash_suite.mac_b(response.c_b, alice_state.m1)
    if not np.array_equal(expected_h_b, response.h_b):
        raise LCLAError("INVALID_RESPONDER_MAC", "h_B 验证失败")
    profile = context.profile
    sampler = DiscreteGaussianSampler(
        beta=profile.beta,
        seed=seed,
        exponent_variant=(
            "paper_definition3"
            if context.distribution_variant == "paper_literal_distribution"
            else "standard_lattice"
        ),
    )
    e_b_vector = map_centered_to_zq(sampler.sample((profile.m,)).centered, q=profile.q)
    n_b_prime = vector_add_mod(
        matrix_vector_mod(
            response.c_b,
            alice_key_pair.private_key.combined_s,
            q=profile.q,
            backend=context.backend,
        ),
        scalar_multiply_mod(2, e_b_vector, q=profile.q),
        q=profile.q,
    )
    signal_b = signal(n_b_prime, q=profile.q, seed=seed + 1_000_033)
    m2 = mod2(n_b_prime, signal_b.delta, q=profile.q)
    mask = context.hash_suite.identity_mask(
        signal_b.delta,
        request.h_a,
        response.c_b,
        alice_state.m1,
        output_length=len(identity_a),
    )
    t_a = xor_identity(identity_a, mask)
    finish = LCLAAliceFinish(
        t_a=t_a,
        delta_b=signal_b.delta,
        q=profile.q,
        profile=profile.name,
        backend=context.backend,
    )
    final_state = replace(
        alice_state,
        e_b_vector=e_b_vector,
        n_b_prime=n_b_prime,
        m2=m2,
    )
    literal_key, audited_key = context.hash_suite.session_key(
        identity_a, identity_b, alice_state.m1, m2
    )
    digest = transcript_hash(
        request_c_a=request.c_a,
        request_delta_a=request.delta_a,
        request_h_a=request.h_a,
        response_c_b=response.c_b,
        response_h_b=response.h_b,
        finish_t_a=finish.t_a,
        finish_delta_b=finish.delta_b,
        profile=profile,
    )
    result = LCLASessionResult(
        accepted=True,
        local_identity=identity_a,
        peer_identity=identity_b,
        shared_bits=LCLASharedBits(m1=alice_state.m1, m2=m2),
        session_key_bits=literal_key,
        session_key_bytes=audited_key,
        transcript_hash=digest,
        profile=profile.name,
        backend=context.backend,
        keygen_backend=context.keygen_backend,
        distribution_variant=context.distribution_variant,
    )
    return finish, final_state, result


def bob_finish(
    context: LCLAProtocolContext,
    bob_key_pair: LCLAStaticKeyPair,
    bob_identity: str | bytes,
    request: LCLAAliceRequest,
    response: LCLABobResponse,
    bob_state: LCLABobEphemeralState,
    finish: LCLAAliceFinish,
) -> LCLASessionResult:
    """Bob 恢复 ID_A、计算 m2 和会话密钥。"""

    identity_b = _check_key_context(context, bob_key_pair, bob_identity)
    _check_packet_context(
        context,
        q=finish.q,
        profile=finish.profile,
        backend=finish.backend,
    )
    if (
        bob_state.q != context.profile.q
        or bob_state.profile != context.profile.name
        or bob_state.backend != context.backend
        or bob_state.distribution_variant != context.distribution_variant
    ):
        raise LCLAError("CONTEXT_ERROR", "Bob ephemeral state 上下文不一致")
    mask = context.hash_suite.identity_mask(
        finish.delta_b,
        request.h_a,
        response.c_b,
        bob_state.m1_prime,
        output_length=len(finish.t_a),
    )
    recovered_identity = xor_identity(finish.t_a, mask)
    if not recovered_identity:
        raise LCLAError("ID_RECOVERY_FAILURE", "恢复 identity 为空")
    if context.hash_suite.programmed and not context.hash_suite.has_registered_identity(
        recovered_identity
    ):
        raise LCLAError("ID_RECOVERY_FAILURE", "恢复 identity 未在 H1 registry 中注册")
    try:
        recovered_identity.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LCLAError("ID_RECOVERY_FAILURE", "恢复 identity 不是合法 UTF-8") from exc
    pk_a = context.hash_suite.h1(recovered_identity)
    n_b = transpose_matrix_vector_mod(
        bob_state.x_b, pk_a, q=context.profile.q, backend=context.backend
    )
    m2_prime = mod2(n_b, finish.delta_b, q=context.profile.q)
    literal_key, audited_key = context.hash_suite.session_key(
        recovered_identity,
        identity_b,
        bob_state.m1_prime,
        m2_prime,
    )
    digest = transcript_hash(
        request_c_a=request.c_a,
        request_delta_a=request.delta_a,
        request_h_a=request.h_a,
        response_c_b=response.c_b,
        response_h_b=response.h_b,
        finish_t_a=finish.t_a,
        finish_delta_b=finish.delta_b,
        profile=context.profile,
    )
    return LCLASessionResult(
        accepted=True,
        local_identity=identity_b,
        peer_identity=recovered_identity,
        shared_bits=LCLASharedBits(m1=bob_state.m1_prime, m2=m2_prime),
        session_key_bits=literal_key,
        session_key_bytes=audited_key,
        transcript_hash=digest,
        profile=context.profile.name,
        backend=context.backend,
        keygen_backend=context.keygen_backend,
        distribution_variant=context.distribution_variant,
    )


def validate_session_pair(alice_result: LCLASessionResult, bob_result: LCLASessionResult) -> None:
    """显式检查 m1/m2/key/identity/transcript 一致性。"""

    if alice_result.distribution_variant != bob_result.distribution_variant:
        raise LCLAError("CONTEXT_ERROR", "双方 distribution variant 不一致")
    if alice_result.local_identity != bob_result.peer_identity:
        raise LCLAError("ID_RECOVERY_FAILURE", "Bob 恢复的 Alice identity 不一致")
    if alice_result.peer_identity != bob_result.local_identity:
        raise LCLAError("IDENTITY_ERROR", "双方 peer identity 不一致")
    if not np.array_equal(
        alice_result.shared_bits.m1, bob_result.shared_bits.m1
    ) or not np.array_equal(alice_result.shared_bits.m2, bob_result.shared_bits.m2):
        raise LCLAError("RECONCILIATION_FAILURE", "m1 或 m2 不一致")
    if (
        alice_result.session_key_bits != bob_result.session_key_bits
        or alice_result.session_key_bytes != bob_result.session_key_bytes
    ):
        raise LCLAError("SESSION_KEY_MISMATCH", "双方 session key 不一致")
    if alice_result.transcript_hash != bob_result.transcript_hash:
        raise LCLAError("TRANSCRIPT_MISMATCH", "双方 transcript hash 不一致")


def run_lcla_handshake(
    context: LCLAProtocolContext,
    alice_key_pair: LCLAStaticKeyPair,
    bob_key_pair: LCLAStaticKeyPair,
    alice_identity: str | bytes,
    bob_identity: str | bytes,
    *,
    initiator_seed: int,
    responder_seed: int,
    finish_seed: int | None = None,
) -> LCLAHandshakeTrace:
    """不跳过任何协议步骤的完整三轮握手。"""

    actual_finish_seed = finish_seed if finish_seed is not None else initiator_seed + 2_000_003
    request, alice_state = alice_create_request(
        context,
        alice_key_pair,
        alice_identity,
        bob_identity,
        seed=initiator_seed,
    )
    response, bob_state = bob_respond(
        context,
        bob_key_pair,
        bob_identity,
        request,
        seed=responder_seed,
    )
    finish, final_alice_state, alice_result = alice_finish(
        context,
        alice_key_pair,
        alice_identity,
        bob_identity,
        request,
        alice_state,
        response,
        seed=actual_finish_seed,
    )
    bob_result = bob_finish(
        context,
        bob_key_pair,
        bob_identity,
        request,
        response,
        bob_state,
        finish,
    )
    validate_session_pair(alice_result, bob_result)
    return LCLAHandshakeTrace(
        request=request,
        response=response,
        finish=finish,
        alice_state=final_alice_state,
        bob_state=bob_state,
        alice_result=alice_result,
        bob_result=bob_result,
        initiator_authentication=True,
        responder_authentication=True,
        m1_consistency=True,
        m2_consistency=True,
        session_key_consistency=True,
        distribution_variant=context.distribution_variant,
    )
