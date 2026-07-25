"""LCLA-AKA 的冻结数据结构与数组不变量。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

import numpy as np
import numpy.typing as npt

if TYPE_CHECKING:
    from lattice_aka_repro.lcla_hashes import LCLAHashSuite

IntArray = npt.NDArray[np.int64]
BackendName = Literal["safe", "fast"]


class LCLAError(ValueError):
    """携带稳定错误码的 LCLA-AKA 异常。"""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def freeze_integer_array(
    value: npt.ArrayLike,
    *,
    shape: tuple[int, ...],
    q: int | None = None,
    bits: bool = False,
    name: str,
) -> IntArray:
    """复制整数数组、校验 shape/domain，并设置只读。"""

    raw = np.asarray(value)
    if not np.issubdtype(raw.dtype, np.integer):
        raise LCLAError("DTYPE_ERROR", f"{name} 必须使用整数 dtype")
    if raw.shape != shape:
        raise LCLAError("SHAPE_ERROR", f"{name} shape={raw.shape}，预期 {shape}")
    array = np.array(raw, dtype=np.int64, copy=True)
    if bits:
        if np.any((array != 0) & (array != 1)):
            raise LCLAError("DOMAIN_ERROR", f"{name} 必须属于 {{0,1}}")
    elif q is not None and (np.any(array < 0) or np.any(array >= q)):
        raise LCLAError("DOMAIN_ERROR", f"{name} 必须属于 [0,q-1]")
    array.setflags(write=False)
    return array


@dataclass(frozen=True, slots=True)
class LCLAProfile:
    """冻结后的参数 profile。"""

    name: str
    family: str
    m: int
    n: int
    q: int
    beta: float
    q_must_be_prime: bool

    def __post_init__(self) -> None:
        if not self.name or self.family not in {"paper_literal", "audited", "toy"}:
            raise LCLAError("PROFILE_ERROR", "profile 名称或 family 非法")
        if self.m <= 0 or self.n <= 0 or self.q <= 2 or self.beta <= 0:
            raise LCLAError("PROFILE_ERROR", "m/n/q/beta 必须为正且 q>2")
        if self.q % 2 == 0:
            raise LCLAError("PROFILE_ERROR", "reconciliation 要求奇数 q")


@dataclass(frozen=True, slots=True)
class LCLABackendCapabilities:
    """后端能力声明。"""

    name: str
    real_trapdoor: bool
    sample_pre: bool
    arbitrary_parameters: bool
    programmed_h1: bool
    status: str


@dataclass(frozen=True, slots=True)
class LCLATrapdoorHandle:
    """不透明 trapdoor 句柄；unavailable 不伪造秘密材料。"""

    backend: str
    status: str
    opaque_reference: str | None = None


@dataclass(frozen=True, slots=True)
class LCLAParameters:
    """公共参数。"""

    profile: LCLAProfile
    backend: BackendName
    keygen_backend: str
    matrix_a: IntArray
    hash_suite: LCLAHashSuite
    trapdoor: LCLATrapdoorHandle

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "matrix_a",
            freeze_integer_array(
                self.matrix_a,
                shape=(self.profile.n, self.profile.m),
                q=self.profile.q,
                name="A",
            ),
        )


@dataclass(frozen=True, slots=True)
class LCLAEntityContribution:
    """实体生成的 s1、f、u1 及 constructed 后端内部候选 s2。"""

    identity: bytes
    s1: IntArray
    error_f: IntArray
    entity_share_u1: IntArray
    pk_full: IntArray
    constructed_s2: IntArray
    q: int
    profile: str
    backend: BackendName
    keygen_backend: str

    def __post_init__(self) -> None:
        if not self.identity:
            raise LCLAError("IDENTITY_ERROR", "identity 不能为空")
        m = int(np.asarray(self.s1).size)
        n = int(np.asarray(self.error_f).size)
        object.__setattr__(self, "identity", bytes(self.identity))
        object.__setattr__(
            self, "s1", freeze_integer_array(self.s1, shape=(m,), q=self.q, name="s1")
        )
        object.__setattr__(
            self,
            "error_f",
            freeze_integer_array(self.error_f, shape=(n,), q=self.q, name="f"),
        )
        object.__setattr__(
            self,
            "entity_share_u1",
            freeze_integer_array(
                self.entity_share_u1, shape=(n,), q=self.q, name="entity_share_u1"
            ),
        )
        object.__setattr__(
            self,
            "pk_full",
            freeze_integer_array(self.pk_full, shape=(n,), q=self.q, name="pk_full"),
        )
        object.__setattr__(
            self,
            "constructed_s2",
            freeze_integer_array(self.constructed_s2, shape=(m,), q=self.q, name="constructed_s2"),
        )


@dataclass(frozen=True, slots=True)
class LCLAKGCShare:
    """KGC 返回的公开 s2 及目标 u2。"""

    identity: bytes
    kgc_share_s2: IntArray
    kgc_target_u2: IntArray
    programmed_h1: bool
    trapdoor_used: bool
    sample_pre_used: bool
    q: int
    profile: str
    backend: BackendName
    keygen_backend: str

    def __post_init__(self) -> None:
        m = int(np.asarray(self.kgc_share_s2).size)
        n = int(np.asarray(self.kgc_target_u2).size)
        object.__setattr__(self, "identity", bytes(self.identity))
        object.__setattr__(
            self,
            "kgc_share_s2",
            freeze_integer_array(self.kgc_share_s2, shape=(m,), q=self.q, name="kgc_share_s2"),
        )
        object.__setattr__(
            self,
            "kgc_target_u2",
            freeze_integer_array(self.kgc_target_u2, shape=(n,), q=self.q, name="kgc_target_u2"),
        )


@dataclass(frozen=True, slots=True)
class LCLAStaticPublicComponents:
    """静态公开分量，避免与 pk_full 混名。"""

    identity: bytes
    pk_full: IntArray
    entity_share_u1: IntArray
    kgc_target_u2: IntArray
    q: int
    profile: str
    backend: BackendName
    keygen_backend: str

    def __post_init__(self) -> None:
        n = int(np.asarray(self.pk_full).size)
        object.__setattr__(self, "identity", bytes(self.identity))
        for field_name in ("pk_full", "entity_share_u1", "kgc_target_u2"):
            object.__setattr__(
                self,
                field_name,
                freeze_integer_array(
                    getattr(self, field_name), shape=(n,), q=self.q, name=field_name
                ),
            )


@dataclass(frozen=True, slots=True)
class LCLAStaticPrivateKey:
    """实体静态私钥；s2 在 literal 口径中可公开。"""

    identity: bytes
    s1: IntArray
    kgc_share_s2: IntArray
    combined_s: IntArray
    error_f: IntArray
    q: int
    profile: str
    backend: BackendName
    keygen_backend: str

    def __post_init__(self) -> None:
        m = int(np.asarray(self.s1).size)
        n = int(np.asarray(self.error_f).size)
        object.__setattr__(self, "identity", bytes(self.identity))
        for field_name in ("s1", "kgc_share_s2", "combined_s"):
            object.__setattr__(
                self,
                field_name,
                freeze_integer_array(
                    getattr(self, field_name), shape=(m,), q=self.q, name=field_name
                ),
            )
        object.__setattr__(
            self,
            "error_f",
            freeze_integer_array(self.error_f, shape=(n,), q=self.q, name="error_f"),
        )


@dataclass(frozen=True, slots=True)
class LCLAStaticKeyPair:
    """类型化静态密钥对。"""

    public_components: LCLAStaticPublicComponents
    private_key: LCLAStaticPrivateKey
    programmed_h1: bool
    trapdoor_used: bool
    sample_pre_used: bool

    def __post_init__(self) -> None:
        if self.public_components.identity != self.private_key.identity:
            raise LCLAError("IDENTITY_ERROR", "静态公私钥 identity 不一致")
        if (
            self.public_components.q != self.private_key.q
            or self.public_components.profile != self.private_key.profile
            or self.public_components.backend != self.private_key.backend
        ):
            raise LCLAError("CONTEXT_ERROR", "静态公私钥上下文不一致")


@dataclass(frozen=True, slots=True)
class LCLAAliceRequest:
    """第一轮公开 packet：C_A、delta_A、h_A。"""

    c_a: IntArray
    delta_a: IntArray
    h_a: IntArray
    q: int
    profile: str
    backend: BackendName

    def __post_init__(self) -> None:
        m = int(np.asarray(self.delta_a).size)
        object.__setattr__(
            self, "c_a", freeze_integer_array(self.c_a, shape=(m, m), q=self.q, name="C_A")
        )
        object.__setattr__(
            self,
            "delta_a",
            freeze_integer_array(self.delta_a, shape=(m,), bits=True, name="delta_A"),
        )
        object.__setattr__(
            self, "h_a", freeze_integer_array(self.h_a, shape=(m,), bits=True, name="h_A")
        )


@dataclass(frozen=True, slots=True)
class LCLABobResponse:
    """第二轮公开 packet：C_B、h_B。"""

    c_b: IntArray
    h_b: IntArray
    q: int
    profile: str
    backend: BackendName

    def __post_init__(self) -> None:
        m = int(np.asarray(self.h_b).size)
        object.__setattr__(
            self, "c_b", freeze_integer_array(self.c_b, shape=(m, m), q=self.q, name="C_B")
        )
        object.__setattr__(
            self, "h_b", freeze_integer_array(self.h_b, shape=(m,), bits=True, name="h_B")
        )


@dataclass(frozen=True, slots=True)
class LCLAAliceFinish:
    """第三轮公开 packet：T_A、delta_B。"""

    t_a: bytes
    delta_b: IntArray
    q: int
    profile: str
    backend: BackendName

    def __post_init__(self) -> None:
        if not self.t_a:
            raise LCLAError("ID_RECOVERY_FAILURE", "T_A 不能为空")
        m = int(np.asarray(self.delta_b).size)
        object.__setattr__(self, "t_a", bytes(self.t_a))
        object.__setattr__(
            self,
            "delta_b",
            freeze_integer_array(self.delta_b, shape=(m,), bits=True, name="delta_B"),
        )


@dataclass(frozen=True, slots=True)
class LCLAAliceEphemeralState:
    """Alice 本地 ephemeral secret 与中间量。"""

    x_a: IntArray
    e_a_matrix: IntArray
    e_a_vector: IntArray
    n_a: IntArray
    m1: IntArray
    signal_random_bits_a: IntArray
    e_b_vector: IntArray | None
    n_b_prime: IntArray | None
    m2: IntArray | None
    q: int
    profile: str
    backend: BackendName

    def __post_init__(self) -> None:
        n, m = np.asarray(self.x_a).shape
        object.__setattr__(
            self, "x_a", freeze_integer_array(self.x_a, shape=(n, m), q=self.q, name="X_A")
        )
        object.__setattr__(
            self,
            "e_a_matrix",
            freeze_integer_array(self.e_a_matrix, shape=(m, m), q=self.q, name="E_A"),
        )
        for field_name in ("e_a_vector", "n_a"):
            object.__setattr__(
                self,
                field_name,
                freeze_integer_array(
                    getattr(self, field_name), shape=(m,), q=self.q, name=field_name
                ),
            )
        for field_name in ("m1", "signal_random_bits_a"):
            object.__setattr__(
                self,
                field_name,
                freeze_integer_array(
                    getattr(self, field_name), shape=(m,), bits=True, name=field_name
                ),
            )
        if self.e_b_vector is not None:
            object.__setattr__(
                self,
                "e_b_vector",
                freeze_integer_array(self.e_b_vector, shape=(m,), q=self.q, name="e_B"),
            )
        if self.n_b_prime is not None:
            object.__setattr__(
                self,
                "n_b_prime",
                freeze_integer_array(self.n_b_prime, shape=(m,), q=self.q, name="n_B_prime"),
            )
        if self.m2 is not None:
            object.__setattr__(
                self,
                "m2",
                freeze_integer_array(self.m2, shape=(m,), bits=True, name="m2"),
            )


@dataclass(frozen=True, slots=True)
class LCLABobEphemeralState:
    """Bob 本地 ephemeral secret 与共享 m1。"""

    x_b: IntArray
    e_b_matrix: IntArray
    n_a_prime: IntArray
    m1_prime: IntArray
    q: int
    profile: str
    backend: BackendName

    def __post_init__(self) -> None:
        n, m = np.asarray(self.x_b).shape
        object.__setattr__(
            self, "x_b", freeze_integer_array(self.x_b, shape=(n, m), q=self.q, name="X_B")
        )
        object.__setattr__(
            self,
            "e_b_matrix",
            freeze_integer_array(self.e_b_matrix, shape=(m, m), q=self.q, name="E_B"),
        )
        object.__setattr__(
            self,
            "n_a_prime",
            freeze_integer_array(self.n_a_prime, shape=(m,), q=self.q, name="n_A_prime"),
        )
        object.__setattr__(
            self,
            "m1_prime",
            freeze_integer_array(self.m1_prime, shape=(m,), bits=True, name="m1_prime"),
        )


@dataclass(frozen=True, slots=True)
class LCLASharedBits:
    """双方 reconciliation 产生的 m1/m2。"""

    m1: IntArray
    m2: IntArray

    def __post_init__(self) -> None:
        m = int(np.asarray(self.m1).size)
        object.__setattr__(
            self, "m1", freeze_integer_array(self.m1, shape=(m,), bits=True, name="m1")
        )
        object.__setattr__(
            self, "m2", freeze_integer_array(self.m2, shape=(m,), bits=True, name="m2")
        )


@dataclass(frozen=True, slots=True)
class LCLASessionResult:
    """单方会话结果。"""

    accepted: bool
    local_identity: bytes
    peer_identity: bytes
    shared_bits: LCLASharedBits
    session_key_bits: bytes
    session_key_bytes: bytes | None
    transcript_hash: bytes
    profile: str
    backend: BackendName
    keygen_backend: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "local_identity", bytes(self.local_identity))
        object.__setattr__(self, "peer_identity", bytes(self.peer_identity))
        object.__setattr__(self, "session_key_bits", bytes(self.session_key_bits))
        object.__setattr__(self, "transcript_hash", bytes(self.transcript_hash))
        if self.session_key_bytes is not None:
            object.__setattr__(self, "session_key_bytes", bytes(self.session_key_bytes))
        if self.accepted and (not self.local_identity or not self.peer_identity):
            raise LCLAError("IDENTITY_ERROR", "accepted session identity 不能为空")


@dataclass(frozen=True, slots=True)
class LCLAProtocolContext:
    """协议上下文。"""

    parameters: LCLAParameters
    hash_suite: LCLAHashSuite
    profile: LCLAProfile
    backend: BackendName
    keygen_backend: str

    def __post_init__(self) -> None:
        if self.parameters.profile != self.profile:
            raise LCLAError("CONTEXT_ERROR", "parameters/profile 不一致")
        if self.parameters.backend != self.backend:
            raise LCLAError("CONTEXT_ERROR", "parameters/backend 不一致")
