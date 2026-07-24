"""C2LAKE 完整协议协商复现。

本模块实现 C2LAKE 论文 Section 5.5 的 Alice/Bob 认证密钥协商流程。
实现边界仅覆盖可执行正确性、消息认证验证式、K1/K2/K3 一致性和会话密钥一致性；
不实现 eCK game、安全归约、ISIS/CBi-ISIS 求解器或任何安全性证明。
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Final, Literal, TypeAlias, cast

import numpy as np
import numpy.typing as npt

from lattice_aka_repro.c2lake_core import (
    ArrayI64,
    BackendName,
    C2LakeCoreError,
    C2LakeKeyPair,
    C2LakePublicParameters,
    bounded_ternary_vector,
    dot_mod,
    matrix_times_vector,
    vector_times_matrix,
    zq_add,
    zq_scalar_mul,
)
from lattice_aka_repro.randomness import seeded_rng

ProtocolRole: TypeAlias = Literal["initiator", "responder"]

_ALLOWED_BACKENDS: Final = frozenset({"safe", "fast"})
_SESSION_KDF_LABEL: Final = b"C2LAKE-SESSION-KDF-v1"
_TRANSCRIPT_HASH_LABEL: Final = b"C2LAKE-HANDSHAKE-TRANSCRIPT-v1"
_REQUEST_HASH_LABEL: Final = b"C2LAKE-REQUEST-TRANSCRIPT-v1"
_RESPONSE_HASH_LABEL: Final = b"C2LAKE-RESPONSE-TRANSCRIPT-v1"


@dataclass(frozen=True, slots=True)
class C2LakeTimestampPolicy:
    """显式时间戳策略；本项目统一使用整数秒。"""

    max_clock_skew: int
    max_message_age: int
    time_unit: Literal["seconds"] = field(init=False, default="seconds")

    def __post_init__(self) -> None:
        _validate_nonnegative_int(self.max_clock_skew, "max_clock_skew", code="INVALID_TIMESTAMP")
        _validate_nonnegative_int(
            self.max_message_age,
            "max_message_age",
            code="INVALID_TIMESTAMP",
        )

    def validate(self, timestamp: int, *, now: int) -> None:
        checked_timestamp = _validate_timestamp_value(timestamp)
        checked_now = _validate_timestamp_value(now, name="now")
        if checked_timestamp > checked_now + self.max_clock_skew:
            raise C2LakeCoreError("TIMESTAMP_IN_FUTURE", "消息时间戳超过未来容差")
        if checked_now - checked_timestamp > self.max_message_age:
            raise C2LakeCoreError("MESSAGE_EXPIRED", "消息时间戳超过最大允许年龄")


@dataclass(frozen=True, slots=True, eq=False)
class C2LakeProtocolContext:
    """单个参与方的长期协议上下文。"""

    identity: bytes
    public_params: C2LakePublicParameters
    key_pair: C2LakeKeyPair
    n: int = field(init=False)
    q: int = field(init=False)
    profile: str = field(init=False)
    backend: BackendName = field(init=False)

    def __post_init__(self) -> None:
        identity = _normalize_identity(self.identity)
        _ensure_key_pair_context(self.public_params, self.key_pair)
        if self.key_pair.identity != identity:
            raise C2LakeCoreError("IDENTITY_ERROR", "identity 与 key_pair 不一致")
        object.__setattr__(self, "identity", identity)
        object.__setattr__(self, "n", self.public_params.n)
        object.__setattr__(self, "q", self.public_params.q)
        object.__setattr__(self, "profile", self.public_params.profile)
        object.__setattr__(self, "backend", self.public_params.backend)


@dataclass(frozen=True, slots=True, eq=False)
class C2LakeRequest:
    """Alice -> Bob 公开请求 transcript。"""

    identity: bytes
    q: int
    profile: str
    backend: BackendName
    n: int
    p_i0: ArrayI64
    p_i1: ArrayI64
    x_i_public: ArrayI64
    y_i_public: ArrayI64
    z_i_public: ArrayI64
    s_i: ArrayI64
    timestamp: int
    array_copy_policy: str = field(init=False, default="copy_and_mark_readonly")
    arrays_readonly: bool = field(init=False, default=True)

    def __post_init__(self) -> None:
        _validate_message_common(self)
        object.__setattr__(self, "identity", _normalize_identity(self.identity))
        object.__setattr__(self, "p_i0", _readonly_protocol_vector(self.p_i0, self))
        object.__setattr__(self, "p_i1", _readonly_protocol_vector(self.p_i1, self))
        object.__setattr__(self, "x_i_public", _readonly_protocol_vector(self.x_i_public, self))
        object.__setattr__(self, "y_i_public", _readonly_protocol_vector(self.y_i_public, self))
        object.__setattr__(self, "z_i_public", _readonly_protocol_vector(self.z_i_public, self))
        object.__setattr__(self, "s_i", _readonly_protocol_vector(self.s_i, self))
        object.__setattr__(self, "timestamp", _validate_timestamp_value(self.timestamp))


@dataclass(frozen=True, slots=True, eq=False)
class C2LakeResponse:
    """Bob -> Alice 公开响应 transcript。"""

    identity: bytes
    q: int
    profile: str
    backend: BackendName
    n: int
    p_j0: ArrayI64
    p_j1: ArrayI64
    x_j_public: ArrayI64
    y_j_public: ArrayI64
    z_j_public: ArrayI64
    s_j: ArrayI64
    timestamp: int
    array_copy_policy: str = field(init=False, default="copy_and_mark_readonly")
    arrays_readonly: bool = field(init=False, default=True)

    def __post_init__(self) -> None:
        _validate_message_common(self)
        object.__setattr__(self, "identity", _normalize_identity(self.identity))
        object.__setattr__(self, "p_j0", _readonly_protocol_vector(self.p_j0, self))
        object.__setattr__(self, "p_j1", _readonly_protocol_vector(self.p_j1, self))
        object.__setattr__(self, "x_j_public", _readonly_protocol_vector(self.x_j_public, self))
        object.__setattr__(self, "y_j_public", _readonly_protocol_vector(self.y_j_public, self))
        object.__setattr__(self, "z_j_public", _readonly_protocol_vector(self.z_j_public, self))
        object.__setattr__(self, "s_j", _readonly_protocol_vector(self.s_j, self))
        object.__setattr__(self, "timestamp", _validate_timestamp_value(self.timestamp))


@dataclass(frozen=True, slots=True, eq=False)
class C2LakeInitiatorEphemeralState:
    """Alice 本地 ephemeral secret；不得出现在公开 transcript 中。"""

    identity: bytes
    peer_identity: bytes
    q: int
    profile: str
    backend: BackendName
    n: int
    x_i: ArrayI64
    y_i: ArrayI64
    z_i: ArrayI64
    timestamp: int
    request_transcript_hash: str
    array_copy_policy: str = field(init=False, default="copy_and_mark_readonly")
    arrays_readonly: bool = field(init=False, default=True)

    def __post_init__(self) -> None:
        _validate_state_common(self)
        object.__setattr__(self, "identity", _normalize_identity(self.identity))
        object.__setattr__(self, "peer_identity", _normalize_identity(self.peer_identity))
        object.__setattr__(self, "x_i", _readonly_protocol_vector(self.x_i, self))
        object.__setattr__(self, "y_i", _readonly_protocol_vector(self.y_i, self))
        object.__setattr__(self, "z_i", _readonly_protocol_vector(self.z_i, self))
        object.__setattr__(self, "timestamp", _validate_timestamp_value(self.timestamp))
        _validate_hex_digest(self.request_transcript_hash, "request_transcript_hash")


@dataclass(frozen=True, slots=True, eq=False)
class C2LakeResponderEphemeralState:
    """Bob 本地 ephemeral secret 与本地已派生共享分量。"""

    identity: bytes
    peer_identity: bytes
    q: int
    profile: str
    backend: BackendName
    n: int
    x_j: ArrayI64
    y_j: ArrayI64
    z_j: ArrayI64
    timestamp: int
    request_transcript_hash: str
    response_transcript_hash: str
    components: C2LakeSharedComponents
    array_copy_policy: str = field(init=False, default="copy_and_mark_readonly")
    arrays_readonly: bool = field(init=False, default=True)

    def __post_init__(self) -> None:
        _validate_state_common(self)
        object.__setattr__(self, "identity", _normalize_identity(self.identity))
        object.__setattr__(self, "peer_identity", _normalize_identity(self.peer_identity))
        object.__setattr__(self, "x_j", _readonly_protocol_vector(self.x_j, self))
        object.__setattr__(self, "y_j", _readonly_protocol_vector(self.y_j, self))
        object.__setattr__(self, "z_j", _readonly_protocol_vector(self.z_j, self))
        object.__setattr__(self, "timestamp", _validate_timestamp_value(self.timestamp))
        _validate_hex_digest(self.request_transcript_hash, "request_transcript_hash")
        _validate_hex_digest(self.response_transcript_hash, "response_transcript_hash")
        _ensure_shared_component_context(self, self.components, "components")


@dataclass(frozen=True, slots=True)
class C2LakeSharedComponents:
    """会话共享分量 K1、K2、K3，均为 Zq 标量。"""

    k1: int
    k2: int
    k3: int
    q: int
    profile: str
    backend: BackendName

    def __post_init__(self) -> None:
        _validate_q(self.q)
        object.__setattr__(self, "backend", _validate_backend(self.backend))
        _validate_profile_name(self.profile)
        object.__setattr__(self, "k1", _validate_zq_scalar(self.k1, self.q, "K1"))
        object.__setattr__(self, "k2", _validate_zq_scalar(self.k2, self.q, "K2"))
        object.__setattr__(self, "k3", _validate_zq_scalar(self.k3, self.q, "K3"))


@dataclass(frozen=True, slots=True)
class C2LakeSessionResult:
    """单方完成握手后的会话结果。"""

    accepted: bool
    role: ProtocolRole
    local_identity: bytes
    peer_identity: bytes
    transcript_hash: str
    components: C2LakeSharedComponents
    session_key_scalar: int
    session_key_bytes: bytes | None
    q: int
    profile: str
    backend: BackendName
    error_code: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.accepted, bool):
            raise C2LakeCoreError("DTYPE_ERROR", "accepted 必须是 bool")
        object.__setattr__(self, "local_identity", _normalize_identity(self.local_identity))
        object.__setattr__(self, "peer_identity", _normalize_identity(self.peer_identity))
        _validate_hex_digest(self.transcript_hash, "transcript_hash")
        _validate_q(self.q)
        object.__setattr__(self, "backend", _validate_backend(self.backend))
        _validate_profile_name(self.profile)
        _ensure_shared_component_context(self, self.components, "components")
        object.__setattr__(
            self,
            "session_key_scalar",
            _validate_zq_star_scalar(self.session_key_scalar, self.q, "session_key_scalar"),
        )
        if self.session_key_bytes is not None:
            if not isinstance(self.session_key_bytes, bytes) or len(self.session_key_bytes) != 32:
                raise C2LakeCoreError("DTYPE_ERROR", "session_key_bytes 必须为 32-byte bytes")
            object.__setattr__(self, "session_key_bytes", bytes(bytearray(self.session_key_bytes)))
        if self.accepted and self.error_code is not None:
            raise C2LakeCoreError("DTYPE_ERROR", "accepted session 不应携带 error_code")


def make_protocol_context(
    public_params: C2LakePublicParameters,
    key_pair: C2LakeKeyPair,
    identity: object,
) -> C2LakeProtocolContext:
    """创建参与方上下文，并显式检查 identity 与长期密钥一致。"""

    return C2LakeProtocolContext(
        identity=_normalize_identity(identity),
        public_params=public_params,
        key_pair=key_pair,
    )


def initiator_create_request(
    context: C2LakeProtocolContext,
    peer_identity: object,
    *,
    timestamp: int,
    seed: int,
) -> tuple[C2LakeRequest, C2LakeInitiatorEphemeralState]:
    """Alice 生成发起请求和本地 ephemeral state。"""

    checked_peer_identity = _normalize_identity(peer_identity)
    checked_timestamp = _validate_timestamp_value(timestamp)
    rng = seeded_rng(seed)
    x_i = _sample_ephemeral_vector(context.public_params, rng)
    y_i = _sample_ephemeral_vector(context.public_params, rng)
    z_i = _sample_ephemeral_vector(context.public_params, rng)
    x_i_public = vector_times_matrix(
        x_i,
        context.public_params.matrix,
        q=context.q,
        backend=context.backend,
    )
    y_i_public = matrix_times_vector(
        context.public_params.matrix,
        y_i,
        q=context.q,
        backend=context.backend,
    )
    z_i_public = matrix_times_vector(
        context.public_params.matrix,
        z_i,
        q=context.q,
        backend=context.backend,
    )
    h2_i = context.public_params.hash_suite.h2(
        context.identity,
        context.key_pair.public_key.p_i0,
        context.key_pair.public_key.p_i1,
        x_i_public,
        y_i_public,
        z_i_public,
        checked_timestamp,
        q=context.q,
    )
    secret_sum = zq_add(
        context.key_pair.private_key.d_i0,
        context.key_pair.private_key.d_i1,
        q=context.q,
    )
    s_i = zq_add(x_i, zq_scalar_mul(h2_i, secret_sum, q=context.q), q=context.q)
    request = C2LakeRequest(
        identity=context.identity,
        q=context.q,
        profile=context.profile,
        backend=context.backend,
        n=context.n,
        p_i0=context.key_pair.public_key.p_i0,
        p_i1=context.key_pair.public_key.p_i1,
        x_i_public=x_i_public,
        y_i_public=y_i_public,
        z_i_public=z_i_public,
        s_i=s_i,
        timestamp=checked_timestamp,
    )
    state = C2LakeInitiatorEphemeralState(
        identity=context.identity,
        peer_identity=checked_peer_identity,
        q=context.q,
        profile=context.profile,
        backend=context.backend,
        n=context.n,
        x_i=x_i,
        y_i=y_i,
        z_i=z_i,
        timestamp=checked_timestamp,
        request_transcript_hash=request_transcript_hash(request),
    )
    return request, state


def responder_verify_and_reply(
    context: C2LakeProtocolContext,
    request: C2LakeRequest,
    *,
    timestamp: int,
    seed: int,
    now: int,
    timestamp_policy: C2LakeTimestampPolicy,
) -> tuple[C2LakeResponse, C2LakeResponderEphemeralState, C2LakeSessionResult]:
    """Bob 验证 Alice 请求，成功后生成响应和 Bob 侧会话结果。"""

    _ensure_message_context(context.public_params, request, "request")
    timestamp_policy.validate(request.timestamp, now=now)
    if not verify_initiator_auth(context.public_params, request):
        raise C2LakeCoreError("INVALID_INITIATOR_AUTH", "Alice 认证验证式不成立")

    checked_timestamp = _validate_timestamp_value(timestamp)
    rng = seeded_rng(seed)
    x_j = _sample_ephemeral_vector(context.public_params, rng)
    y_j = _sample_ephemeral_vector(context.public_params, rng)
    z_j = _sample_ephemeral_vector(context.public_params, rng)
    x_j_public = vector_times_matrix(
        x_j,
        context.public_params.matrix,
        q=context.q,
        backend=context.backend,
    )
    y_j_public = matrix_times_vector(
        context.public_params.matrix,
        y_j,
        q=context.q,
        backend=context.backend,
    )
    z_j_public = matrix_times_vector(
        context.public_params.matrix,
        z_j,
        q=context.q,
        backend=context.backend,
    )
    h2_j = context.public_params.hash_suite.h2(
        context.identity,
        context.key_pair.public_key.p_i0,
        context.key_pair.public_key.p_i1,
        x_j_public,
        y_j_public,
        z_j_public,
        checked_timestamp,
        q=context.q,
    )
    secret_sum = zq_add(
        context.key_pair.private_key.d_i0,
        context.key_pair.private_key.d_i1,
        q=context.q,
    )
    s_j = zq_add(x_j, zq_scalar_mul(h2_j, secret_sum, q=context.q), q=context.q)
    response = C2LakeResponse(
        identity=context.identity,
        q=context.q,
        profile=context.profile,
        backend=context.backend,
        n=context.n,
        p_j0=context.key_pair.public_key.p_i0,
        p_j1=context.key_pair.public_key.p_i1,
        x_j_public=x_j_public,
        y_j_public=y_j_public,
        z_j_public=z_j_public,
        s_j=s_j,
        timestamp=checked_timestamp,
    )
    components = derive_responder_components(context, request, z_j=z_j, y_j=y_j, x_j=x_j)
    result = derive_session_result(
        context.public_params,
        local_identity=context.identity,
        peer_identity=request.identity,
        role="responder",
        request=request,
        response=response,
        components=components,
    )
    state = C2LakeResponderEphemeralState(
        identity=context.identity,
        peer_identity=request.identity,
        q=context.q,
        profile=context.profile,
        backend=context.backend,
        n=context.n,
        x_j=x_j,
        y_j=y_j,
        z_j=z_j,
        timestamp=checked_timestamp,
        request_transcript_hash=request_transcript_hash(request),
        response_transcript_hash=response_transcript_hash(response),
        components=components,
    )
    return response, state, result


def initiator_verify_and_finish(
    context: C2LakeProtocolContext,
    request: C2LakeRequest,
    state: C2LakeInitiatorEphemeralState,
    response: C2LakeResponse,
    *,
    now: int,
    timestamp_policy: C2LakeTimestampPolicy,
) -> C2LakeSessionResult:
    """Alice 验证 Bob 响应，成功后计算 Alice 侧会话结果。"""

    _ensure_message_context(context.public_params, request, "request")
    _ensure_message_context(context.public_params, response, "response")
    _ensure_state_context(context, state, "initiator_state")
    if request_transcript_hash(request) != state.request_transcript_hash:
        raise C2LakeCoreError("TRANSCRIPT_STATE_MISMATCH", "initiator_state 与 request 不匹配")
    if context.identity != request.identity:
        raise C2LakeCoreError("IDENTITY_ERROR", "握手身份与上下文不一致")
    timestamp_policy.validate(response.timestamp, now=now)
    if not verify_responder_auth(context.public_params, response):
        raise C2LakeCoreError("INVALID_RESPONDER_AUTH", "Bob 认证验证式不成立")
    if state.peer_identity != response.identity:
        raise C2LakeCoreError("INVALID_RESPONDER_AUTH", "响应 identity 与发起方预期 peer 不一致")
    components = derive_initiator_components(
        context, response, x_i=state.x_i, y_i=state.y_i, z_i=state.z_i
    )
    return derive_session_result(
        context.public_params,
        local_identity=context.identity,
        peer_identity=response.identity,
        role="initiator",
        request=request,
        response=response,
        components=components,
    )


def run_handshake(
    public_params: C2LakePublicParameters,
    alice_key_pair: C2LakeKeyPair,
    bob_key_pair: C2LakeKeyPair,
    alice_identity: object,
    bob_identity: object,
    initiator_seed: int,
    responder_seed: int,
    initiator_timestamp: int,
    responder_timestamp: int,
    now: int,
    timestamp_policy: C2LakeTimestampPolicy,
) -> tuple[C2LakeSessionResult, C2LakeSessionResult]:
    """运行完整 Alice/Bob 握手，返回 Alice 与 Bob 双方会话结果。"""

    alice_context = make_protocol_context(public_params, alice_key_pair, alice_identity)
    bob_context = make_protocol_context(public_params, bob_key_pair, bob_identity)
    request, initiator_state = initiator_create_request(
        alice_context,
        bob_context.identity,
        timestamp=initiator_timestamp,
        seed=initiator_seed,
    )
    response, _responder_state, responder_result = responder_verify_and_reply(
        bob_context,
        request,
        timestamp=responder_timestamp,
        seed=responder_seed,
        now=now,
        timestamp_policy=timestamp_policy,
    )
    initiator_result = initiator_verify_and_finish(
        alice_context,
        request,
        initiator_state,
        response,
        now=now,
        timestamp_policy=timestamp_policy,
    )
    if initiator_result.components != responder_result.components:
        raise C2LakeCoreError("SESSION_KEY_MISMATCH", "K1/K2/K3 不一致")
    if initiator_result.session_key_scalar != responder_result.session_key_scalar:
        raise C2LakeCoreError("SESSION_KEY_MISMATCH", "H3 scalar 会话密钥不一致")
    if initiator_result.session_key_bytes != responder_result.session_key_bytes:
        raise C2LakeCoreError("SESSION_KEY_MISMATCH", "KDF bytes 会话密钥不一致")
    return initiator_result, responder_result


def verify_initiator_auth(public_params: C2LakePublicParameters, request: C2LakeRequest) -> bool:
    """验证 Alice 请求的 S_i 认证等式。"""

    _ensure_message_context(public_params, request, "request")
    h1_i = public_params.hash_suite.h1(
        request.identity,
        request.p_i0,
        request.p_i1,
        public_params.public_key,
        q=public_params.q,
    )
    h2_i = public_params.hash_suite.h2(
        request.identity,
        request.p_i0,
        request.p_i1,
        request.x_i_public,
        request.y_i_public,
        request.z_i_public,
        request.timestamp,
        q=public_params.q,
    )
    static_public = _static_public_component(
        public_params,
        request.p_i0,
        request.p_i1,
        h1_i,
    )
    lhs = vector_times_matrix(
        request.s_i,
        public_params.matrix,
        q=public_params.q,
        backend=public_params.backend,
    )
    rhs = zq_add(
        request.x_i_public,
        zq_scalar_mul(h2_i, static_public, q=public_params.q),
        q=public_params.q,
    )
    return bool(np.array_equal(lhs, rhs))


def verify_responder_auth(public_params: C2LakePublicParameters, response: C2LakeResponse) -> bool:
    """验证 Bob 响应的 S_j 认证等式。"""

    _ensure_message_context(public_params, response, "response")
    h1_j = public_params.hash_suite.h1(
        response.identity,
        response.p_j0,
        response.p_j1,
        public_params.public_key,
        q=public_params.q,
    )
    h2_j = public_params.hash_suite.h2(
        response.identity,
        response.p_j0,
        response.p_j1,
        response.x_j_public,
        response.y_j_public,
        response.z_j_public,
        response.timestamp,
        q=public_params.q,
    )
    static_public = _static_public_component(
        public_params,
        response.p_j0,
        response.p_j1,
        h1_j,
    )
    lhs = vector_times_matrix(
        response.s_j,
        public_params.matrix,
        q=public_params.q,
        backend=public_params.backend,
    )
    rhs = zq_add(
        response.x_j_public,
        zq_scalar_mul(h2_j, static_public, q=public_params.q),
        q=public_params.q,
    )
    return bool(np.array_equal(lhs, rhs))


def derive_responder_components(
    context: C2LakeProtocolContext,
    request: C2LakeRequest,
    *,
    z_j: npt.ArrayLike,
    y_j: npt.ArrayLike,
    x_j: npt.ArrayLike,
) -> C2LakeSharedComponents:
    """计算 Bob 侧 K_j1、K_j2、K_j3。"""

    _ensure_message_context(context.public_params, request, "request")
    checked_z_j = _readonly_vector(z_j, n=context.n, q=context.q, name="z_j")
    checked_y_j = _readonly_vector(y_j, n=context.n, q=context.q, name="y_j")
    checked_x_j = _readonly_vector(x_j, n=context.n, q=context.q, name="x_j")
    h1_i = context.public_params.hash_suite.h1(
        request.identity,
        request.p_i0,
        request.p_i1,
        context.public_params.public_key,
        q=context.q,
    )
    initiator_static_public = _static_public_component(
        context.public_params,
        request.p_i0,
        request.p_i1,
        h1_i,
    )
    responder_private_sum = zq_add(
        context.key_pair.private_key.d_i0,
        context.key_pair.private_key.d_i1,
        q=context.q,
    )
    k1 = dot_mod(request.x_i_public, checked_y_j, q=context.q, backend=context.backend)
    k2 = dot_mod(checked_x_j, request.y_i_public, q=context.q, backend=context.backend)
    k3_first = dot_mod(
        initiator_static_public,
        checked_z_j,
        q=context.q,
        backend=context.backend,
    )
    k3_second = dot_mod(
        responder_private_sum,
        request.z_i_public,
        q=context.q,
        backend=context.backend,
    )
    return C2LakeSharedComponents(
        k1=k1,
        k2=k2,
        k3=(k3_first + k3_second) % context.q,
        q=context.q,
        profile=context.profile,
        backend=context.backend,
    )


def derive_initiator_components(
    context: C2LakeProtocolContext,
    response: C2LakeResponse,
    *,
    x_i: npt.ArrayLike,
    y_i: npt.ArrayLike,
    z_i: npt.ArrayLike,
) -> C2LakeSharedComponents:
    """计算 Alice 侧 K_i1、K_i2、K_i3。"""

    _ensure_message_context(context.public_params, response, "response")
    checked_x_i = _readonly_vector(x_i, n=context.n, q=context.q, name="x_i")
    checked_y_i = _readonly_vector(y_i, n=context.n, q=context.q, name="y_i")
    checked_z_i = _readonly_vector(z_i, n=context.n, q=context.q, name="z_i")
    h1_j = context.public_params.hash_suite.h1(
        response.identity,
        response.p_j0,
        response.p_j1,
        context.public_params.public_key,
        q=context.q,
    )
    responder_static_public = _static_public_component(
        context.public_params,
        response.p_j0,
        response.p_j1,
        h1_j,
    )
    initiator_private_sum = zq_add(
        context.key_pair.private_key.d_i0,
        context.key_pair.private_key.d_i1,
        q=context.q,
    )
    k1 = dot_mod(checked_x_i, response.y_j_public, q=context.q, backend=context.backend)
    k2 = dot_mod(response.x_j_public, checked_y_i, q=context.q, backend=context.backend)
    k3_first = dot_mod(
        responder_static_public,
        checked_z_i,
        q=context.q,
        backend=context.backend,
    )
    k3_second = dot_mod(
        initiator_private_sum,
        response.z_j_public,
        q=context.q,
        backend=context.backend,
    )
    return C2LakeSharedComponents(
        k1=k1,
        k2=k2,
        k3=(k3_first + k3_second) % context.q,
        q=context.q,
        profile=context.profile,
        backend=context.backend,
    )


def derive_session_result(
    public_params: C2LakePublicParameters,
    *,
    local_identity: bytes,
    peer_identity: bytes,
    role: ProtocolRole,
    request: C2LakeRequest,
    response: C2LakeResponse,
    components: C2LakeSharedComponents,
) -> C2LakeSessionResult:
    """按 canonical H3 字段顺序派生单方会话结果。"""

    _ensure_message_context(public_params, request, "request")
    _ensure_message_context(public_params, response, "response")
    _ensure_shared_component_context(public_params, components, "components")
    h3_payload = encode_h3_transcript(public_params, request, response, components)
    session_key_scalar = public_params.hash_suite.h3(
        request.p_i0,
        request.p_i1,
        request.x_i_public,
        request.y_i_public,
        request.z_i_public,
        response.p_j0,
        response.p_j1,
        response.x_j_public,
        response.y_j_public,
        response.z_j_public,
        components.k1,
        components.k2,
        components.k3,
        q=public_params.q,
    )
    session_key_bytes = None
    if public_params.family in {"audited", "audited_prime"}:
        session_key_bytes = _shake_digest(_SESSION_KDF_LABEL, h3_payload, length=32)
    return C2LakeSessionResult(
        accepted=True,
        role=role,
        local_identity=local_identity,
        peer_identity=peer_identity,
        transcript_hash=_shake_digest_hex(_TRANSCRIPT_HASH_LABEL, h3_payload),
        components=components,
        session_key_scalar=session_key_scalar,
        session_key_bytes=session_key_bytes,
        q=public_params.q,
        profile=public_params.profile,
        backend=public_params.backend,
    )


def encode_h3_transcript(
    public_params: C2LakePublicParameters,
    request: C2LakeRequest,
    response: C2LakeResponse,
    components: C2LakeSharedComponents,
) -> bytes:
    """返回 H3 canonical transcript 编码。"""

    _ensure_message_context(public_params, request, "request")
    _ensure_message_context(public_params, response, "response")
    _ensure_shared_component_context(public_params, components, "components")
    return public_params.hash_suite.encode_h3(
        request.p_i0,
        request.p_i1,
        request.x_i_public,
        request.y_i_public,
        request.z_i_public,
        response.p_j0,
        response.p_j1,
        response.x_j_public,
        response.y_j_public,
        response.z_j_public,
        components.k1,
        components.k2,
        components.k3,
        q=public_params.q,
    )


def request_transcript_hash(request: C2LakeRequest) -> str:
    """公开请求 transcript 哈希，不包含本地 x/y/z secret。"""

    return _shake_digest_hex(_REQUEST_HASH_LABEL, _encode_request(request))


def response_transcript_hash(response: C2LakeResponse) -> str:
    """公开响应 transcript 哈希，不包含本地 x/y/z secret。"""

    return _shake_digest_hex(_RESPONSE_HASH_LABEL, _encode_response(response))


def _static_public_component(
    public_params: C2LakePublicParameters,
    p_0: npt.ArrayLike,
    p_1: npt.ArrayLike,
    h1_value: int,
) -> ArrayI64:
    p0_checked = _readonly_vector(p_0, n=public_params.n, q=public_params.q, name="P_0")
    p1_checked = _readonly_vector(p_1, n=public_params.n, q=public_params.q, name="P_1")
    return zq_add(
        zq_add(p0_checked, p1_checked, q=public_params.q),
        zq_scalar_mul(h1_value, public_params.public_key, q=public_params.q),
        q=public_params.q,
    )


def _sample_ephemeral_vector(
    public_params: C2LakePublicParameters,
    rng: np.random.Generator,
) -> ArrayI64:
    return bounded_ternary_vector(rng, public_params.n, q=public_params.q, beta=public_params.beta)


def _ensure_key_pair_context(
    public_params: C2LakePublicParameters,
    key_pair: C2LakeKeyPair,
) -> None:
    if key_pair.q != public_params.q:
        raise C2LakeCoreError("MODULUS_ERROR", "key_pair q 与 public_params 不一致")
    if key_pair.profile != public_params.profile:
        raise C2LakeCoreError("PROFILE_ERROR", "key_pair profile 与 public_params 不一致")
    if key_pair.backend != public_params.backend:
        raise C2LakeCoreError("BACKEND_ERROR", "key_pair backend 与 public_params 不一致")
    if key_pair.shape != (public_params.n,):
        raise C2LakeCoreError("SHAPE_ERROR", "key_pair shape 与 public_params 不一致")


def _ensure_message_context(
    public_params: C2LakePublicParameters,
    message: C2LakeRequest | C2LakeResponse,
    name: str,
) -> None:
    if message.q != public_params.q:
        raise C2LakeCoreError("MODULUS_ERROR", f"{name} q 与 public_params 不一致")
    if message.profile != public_params.profile:
        raise C2LakeCoreError("PROFILE_ERROR", f"{name} profile 与 public_params 不一致")
    if message.backend != public_params.backend:
        raise C2LakeCoreError("BACKEND_ERROR", f"{name} backend 与 public_params 不一致")
    if message.n != public_params.n:
        raise C2LakeCoreError("SHAPE_ERROR", f"{name} n 与 public_params 不一致")


def _ensure_state_context(
    context: C2LakeProtocolContext,
    state: C2LakeInitiatorEphemeralState | C2LakeResponderEphemeralState,
    name: str,
) -> None:
    if state.q != context.q:
        raise C2LakeCoreError("MODULUS_ERROR", f"{name} q 与 context 不一致")
    if state.profile != context.profile:
        raise C2LakeCoreError("PROFILE_ERROR", f"{name} profile 与 context 不一致")
    if state.backend != context.backend:
        raise C2LakeCoreError("BACKEND_ERROR", f"{name} backend 与 context 不一致")
    if state.n != context.n:
        raise C2LakeCoreError("SHAPE_ERROR", f"{name} n 与 context 不一致")
    if state.identity != context.identity:
        raise C2LakeCoreError("IDENTITY_ERROR", f"{name} identity 与 context 不一致")


def _ensure_shared_component_context(
    expected: (
        C2LakePublicParameters
        | C2LakeInitiatorEphemeralState
        | C2LakeResponderEphemeralState
        | C2LakeSessionResult
    ),
    components: C2LakeSharedComponents,
    name: str,
) -> None:
    if components.q != expected.q:
        raise C2LakeCoreError("MODULUS_ERROR", f"{name} q 与上下文不一致")
    if components.profile != expected.profile:
        raise C2LakeCoreError("PROFILE_ERROR", f"{name} profile 与上下文不一致")
    if components.backend != expected.backend:
        raise C2LakeCoreError("BACKEND_ERROR", f"{name} backend 与上下文不一致")


def _validate_message_common(message: C2LakeRequest | C2LakeResponse) -> None:
    _validate_positive_int(message.n, "n", code="SHAPE_ERROR")
    _validate_q(message.q)
    object.__setattr__(message, "backend", _validate_backend(message.backend))
    _validate_profile_name(message.profile)


def _validate_state_common(
    state: C2LakeInitiatorEphemeralState | C2LakeResponderEphemeralState,
) -> None:
    _validate_positive_int(state.n, "n", code="SHAPE_ERROR")
    _validate_q(state.q)
    object.__setattr__(state, "backend", _validate_backend(state.backend))
    _validate_profile_name(state.profile)


def _readonly_protocol_vector(
    value: npt.ArrayLike,
    owner: (
        C2LakeRequest
        | C2LakeResponse
        | C2LakeInitiatorEphemeralState
        | C2LakeResponderEphemeralState
    ),
) -> ArrayI64:
    return _readonly_vector(value, n=owner.n, q=owner.q, name="protocol_vector")


def _readonly_vector(value: npt.ArrayLike, *, n: int, q: int, name: str) -> ArrayI64:
    _validate_q(q)
    raw = np.asarray(value)
    if raw.dtype == np.dtype(bool) or not np.issubdtype(raw.dtype, np.integer):
        raise C2LakeCoreError("DTYPE_ERROR", f"{name} dtype 必须为整数")
    array = cast(ArrayI64, np.array(raw, dtype=np.int64, copy=True))
    if array.shape != (n,):
        raise C2LakeCoreError("SHAPE_ERROR", f"{name} shape 必须为 ({n},)")
    if np.any(array < 0) or np.any(array >= q):
        raise C2LakeCoreError("DOMAIN_ERROR", f"{name} 元素必须位于 [0,q-1]")
    array.setflags(write=False)
    return array


def _validate_backend(backend: str) -> BackendName:
    if backend not in _ALLOWED_BACKENDS:
        raise C2LakeCoreError("BACKEND_ERROR", f"非法 backend {backend!r}")
    return cast(BackendName, backend)


def _validate_profile_name(profile: str) -> None:
    if not isinstance(profile, str) or not profile:
        raise C2LakeCoreError("PROFILE_ERROR", "profile 必须为非空字符串")


def _validate_q(q: int) -> None:
    _validate_positive_int(q, "q", code="MODULUS_ERROR")
    if q < 2:
        raise C2LakeCoreError("MODULUS_ERROR", "q 必须大于等于 2")


def _validate_positive_int(value: int, name: str, *, code: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise C2LakeCoreError(code, f"{name} 必须是正整数")


def _validate_nonnegative_int(value: int, name: str, *, code: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise C2LakeCoreError(code, f"{name} 必须是非负整数")


def _validate_timestamp_value(timestamp: int, *, name: str = "timestamp") -> int:
    _validate_nonnegative_int(timestamp, name, code="INVALID_TIMESTAMP")
    return timestamp


def _validate_zq_scalar(value: int, q: int, name: str) -> int:
    _validate_q(q)
    if isinstance(value, bool) or not isinstance(value, int):
        raise C2LakeCoreError("DTYPE_ERROR", f"{name} 必须是整数")
    if value < 0 or value >= q:
        raise C2LakeCoreError("DOMAIN_ERROR", f"{name} 必须位于 [0,q-1]")
    return value


def _validate_zq_star_scalar(value: int, q: int, name: str) -> int:
    scalar = _validate_zq_scalar(value, q, name)
    if scalar == 0:
        raise C2LakeCoreError("DOMAIN_ERROR", f"{name} 必须位于 [1,q-1]")
    return scalar


def _validate_hex_digest(value: str, name: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise C2LakeCoreError("DTYPE_ERROR", f"{name} 必须是 32-byte hex digest")
    try:
        bytes.fromhex(value)
    except ValueError as error:
        raise C2LakeCoreError("DTYPE_ERROR", f"{name} 必须是合法十六进制") from error


def _normalize_identity(identity: object) -> bytes:
    if isinstance(identity, str) and identity:
        return identity.encode("utf-8")
    if isinstance(identity, bytes) and identity:
        return bytes(bytearray(identity))
    raise C2LakeCoreError("IDENTITY_ERROR", "identity 必须是非空 bytes 或 str")


def _encode_request(request: C2LakeRequest) -> bytes:
    return b"".join(
        (
            _encode_bytes_field("domain", b"C2LAKE-REQUEST-v1"),
            _encode_identity_field(request.identity),
            _encode_vector_field("P_i0", request.p_i0, q=request.q),
            _encode_vector_field("P_i1", request.p_i1, q=request.q),
            _encode_vector_field("X_i", request.x_i_public, q=request.q),
            _encode_vector_field("Y_i", request.y_i_public, q=request.q),
            _encode_vector_field("Z_i", request.z_i_public, q=request.q),
            _encode_vector_field("S_i", request.s_i, q=request.q),
            _encode_uint_field("T_i", request.timestamp),
        )
    )


def _encode_response(response: C2LakeResponse) -> bytes:
    return b"".join(
        (
            _encode_bytes_field("domain", b"C2LAKE-RESPONSE-v1"),
            _encode_identity_field(response.identity),
            _encode_vector_field("P_j0", response.p_j0, q=response.q),
            _encode_vector_field("P_j1", response.p_j1, q=response.q),
            _encode_vector_field("X_j", response.x_j_public, q=response.q),
            _encode_vector_field("Y_j", response.y_j_public, q=response.q),
            _encode_vector_field("Z_j", response.z_j_public, q=response.q),
            _encode_vector_field("S_j", response.s_j, q=response.q),
            _encode_uint_field("T_j", response.timestamp),
        )
    )


def _encode_field(type_tag: str, payload: bytes) -> bytes:
    tag = type_tag.encode("ascii")
    return tag + len(payload).to_bytes(8, "big") + payload


def _encode_bytes_field(type_tag: str, payload: bytes) -> bytes:
    return _encode_field(type_tag, payload)


def _encode_identity_field(identity: bytes) -> bytes:
    return _encode_field("identity", _normalize_identity(identity))


def _encode_uint_field(type_tag: str, value: int) -> bytes:
    checked = _validate_nonnegative_int_for_encoding(value, type_tag)
    return _encode_field(type_tag, checked.to_bytes(max(1, (checked.bit_length() + 7) // 8), "big"))


def _validate_nonnegative_int_for_encoding(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise C2LakeCoreError("DTYPE_ERROR", f"{name} 必须为非负整数")
    return value


def _encode_vector_field(type_tag: str, value: npt.ArrayLike, *, q: int) -> bytes:
    vector = _readonly_vector(value, n=np.asarray(value).shape[0], q=q, name=type_tag)
    shape_payload = b"".join(
        (
            len(vector.shape).to_bytes(8, "big"),
            vector.shape[0].to_bytes(8, "big"),
            q.to_bytes(8, "big"),
        )
    )
    return _encode_field(
        f"vector:{type_tag}",
        shape_payload + vector.astype(">i8", copy=False).tobytes(order="C"),
    )


def _shake_digest(label: bytes, payload: bytes, *, length: int) -> bytes:
    shake = hashlib.shake_256()
    shake.update(_encode_bytes_field("domain", label))
    shake.update(_encode_bytes_field("payload", payload))
    return shake.digest(length)


def _shake_digest_hex(label: bytes, payload: bytes) -> str:
    return _shake_digest(label, payload, length=32).hex()
