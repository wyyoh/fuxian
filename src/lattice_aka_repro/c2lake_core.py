"""C2LAKE T010 核心：Setup、用户秘密、部分私钥提取与验证。

本模块只实现 T010 授权范围内的可执行性质，不实现 Alice/Bob 协商消息、
K1/K2/K3、会话密钥协商、benchmark 或安全证明验证。
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Literal, TypeAlias, cast

import numpy as np
import numpy.typing as npt

from lattice_aka_repro.errors import ReproductionError
from lattice_aka_repro.profiles import load_profile
from lattice_aka_repro.randomness import seeded_rng

ArrayI64: TypeAlias = npt.NDArray[np.int64]
BackendName: TypeAlias = Literal["safe", "fast"]

_ALLOWED_BACKENDS: Final = frozenset({"safe", "fast"})
_ALLOWED_FAMILIES: Final = frozenset({"paper_literal", "audited", "audited_prime", "toy"})
_ALLOWED_MATRIX_SHAPES: Final = frozenset({"square_n"})
_ALLOWED_SECRET_SAMPLING: Final = frozenset({"literal", "small_secret"})
_MAX_INT64: Final = int(np.iinfo(np.int64).max)


class C2LakeCoreError(ValueError):
    """C2LAKE 核心的稳定错误码异常。"""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True, slots=True)
class C2LakeProfile:
    """已校验的 C2LAKE profile。"""

    name: str
    family: str
    m: int
    n: int
    q: int
    beta: float
    q_must_be_prime: bool
    matrix_shape: str
    secret_sampling: str


@dataclass(frozen=True, slots=True, eq=False)
class C2LakeHashSuite:
    """C2LAKE 哈希接口骨架，使用 SHAKE256 和显式域分离。"""

    h1_label: str = "C2LAKE-H1-v1"
    h2_label: str = "C2LAKE-H2-v1"
    h3_label: str = "C2LAKE-H3-v1"

    def h1(
        self,
        identity: object,
        p_i0: npt.ArrayLike,
        p_i1: npt.ArrayLike,
        public_key: npt.ArrayLike,
        *,
        q: int,
    ) -> int:
        """H1(ID_i, P_i0, P_i1, P) -> [1, q-1]。"""

        payload = self.encode_h1(identity, p_i0, p_i1, public_key, q=q)
        return _shake_to_zq_star(payload, q)

    def h2(
        self,
        identity: object,
        p_i0: npt.ArrayLike,
        p_i1: npt.ArrayLike,
        x_i: npt.ArrayLike,
        y_i: npt.ArrayLike,
        z_i: npt.ArrayLike,
        timestamp: int | bytes | str,
        *,
        q: int,
    ) -> int:
        """H2 类型安全接口骨架；T010 不实现协商消息。"""

        payload = self.encode_h2(identity, p_i0, p_i1, x_i, y_i, z_i, timestamp, q=q)
        return _shake_to_zq_star(payload, q)

    def h3(
        self,
        p_i0: npt.ArrayLike,
        p_i1: npt.ArrayLike,
        x_i: npt.ArrayLike,
        y_i: npt.ArrayLike,
        z_i: npt.ArrayLike,
        p_j0: npt.ArrayLike,
        p_j1: npt.ArrayLike,
        x_j: npt.ArrayLike,
        y_j: npt.ArrayLike,
        z_j: npt.ArrayLike,
        k1: int,
        k2: int,
        k3: int,
        *,
        q: int,
    ) -> int:
        """H3 类型安全接口骨架；T010 不派生会话密钥。"""

        payload = self.encode_h3(
            p_i0,
            p_i1,
            x_i,
            y_i,
            z_i,
            p_j0,
            p_j1,
            x_j,
            y_j,
            z_j,
            k1,
            k2,
            k3,
            q=q,
        )
        return _shake_to_zq_star(payload, q)

    def encode_h1(
        self,
        identity: object,
        p_i0: npt.ArrayLike,
        p_i1: npt.ArrayLike,
        public_key: npt.ArrayLike,
        *,
        q: int,
    ) -> bytes:
        """返回 H1 的长度前缀编码，便于测试编码稳定性。"""

        return b"".join(
            (
                _encode_bytes("domain", self.h1_label.encode("ascii")),
                _encode_identity(identity),
                _encode_vector("P_i0", p_i0, q=q),
                _encode_vector("P_i1", p_i1, q=q),
                _encode_vector("P", public_key, q=q),
            )
        )

    def encode_h2(
        self,
        identity: object,
        p_i0: npt.ArrayLike,
        p_i1: npt.ArrayLike,
        x_i: npt.ArrayLike,
        y_i: npt.ArrayLike,
        z_i: npt.ArrayLike,
        timestamp: int | bytes | str,
        *,
        q: int,
    ) -> bytes:
        """返回 H2 的长度前缀编码。"""

        return b"".join(
            (
                _encode_bytes("domain", self.h2_label.encode("ascii")),
                _encode_identity(identity),
                _encode_vector("P_i0", p_i0, q=q),
                _encode_vector("P_i1", p_i1, q=q),
                _encode_vector("X_i", x_i, q=q),
                _encode_vector("Y_i", y_i, q=q),
                _encode_vector("Z_i", z_i, q=q),
                _encode_timestamp(timestamp),
            )
        )

    def encode_h3(
        self,
        p_i0: npt.ArrayLike,
        p_i1: npt.ArrayLike,
        x_i: npt.ArrayLike,
        y_i: npt.ArrayLike,
        z_i: npt.ArrayLike,
        p_j0: npt.ArrayLike,
        p_j1: npt.ArrayLike,
        x_j: npt.ArrayLike,
        y_j: npt.ArrayLike,
        z_j: npt.ArrayLike,
        k1: int,
        k2: int,
        k3: int,
        *,
        q: int,
    ) -> bytes:
        """返回 H3 的 canonical 字段顺序编码。"""

        return b"".join(
            (
                _encode_bytes("domain", self.h3_label.encode("ascii")),
                _encode_vector("P_i0", p_i0, q=q),
                _encode_vector("P_i1", p_i1, q=q),
                _encode_vector("X_i", x_i, q=q),
                _encode_vector("Y_i", y_i, q=q),
                _encode_vector("Z_i", z_i, q=q),
                _encode_vector("P_j0", p_j0, q=q),
                _encode_vector("P_j1", p_j1, q=q),
                _encode_vector("X_j", x_j, q=q),
                _encode_vector("Y_j", y_j, q=q),
                _encode_vector("Z_j", z_j, q=q),
                _encode_uint("K1", _validate_zq_scalar(k1, q, name="K1")),
                _encode_uint("K2", _validate_zq_scalar(k2, q, name="K2")),
                _encode_uint("K3", _validate_zq_scalar(k3, q, name="K3")),
            )
        )


@dataclass(frozen=True, slots=True, eq=False)
class C2LakePublicParameters:
    """C2LAKE 公共参数 Δ；数组在构造时复制并设为只读。"""

    n: int
    q: int
    beta: float
    profile: str
    family: str
    backend: BackendName
    secret_sampling: str
    matrix: ArrayI64
    public_key: ArrayI64
    hash_suite: C2LakeHashSuite = field(default_factory=C2LakeHashSuite)
    array_copy_policy: str = field(init=False, default="copy_and_mark_readonly")
    arrays_readonly: bool = field(init=False, default=True)

    def __post_init__(self) -> None:
        _validate_positive_int(self.n, "n", code="SHAPE_ERROR")
        _validate_q(self.q)
        _validate_positive_number(self.beta, "beta", code="PROFILE_ERROR")
        object.__setattr__(
            self,
            "backend",
            _validate_backend(self.backend),
        )
        object.__setattr__(
            self,
            "matrix",
            _readonly_zq_matrix(self.matrix, n=self.n, q=self.q, name="M"),
        )
        object.__setattr__(
            self,
            "public_key",
            _readonly_zq_vector(self.public_key, n=self.n, q=self.q, name="P"),
        )


@dataclass(frozen=True, slots=True, eq=False)
class C2LakeMasterSecret:
    """KGC master secret d；数组在构造时复制并设为只读。"""

    q: int
    profile: str
    backend: BackendName
    vector: ArrayI64
    array_copy_policy: str = field(init=False, default="copy_and_mark_readonly")
    arrays_readonly: bool = field(init=False, default=True)

    def __post_init__(self) -> None:
        _validate_q(self.q)
        object.__setattr__(self, "backend", _validate_backend(self.backend))
        object.__setattr__(
            self,
            "vector",
            _readonly_zq_vector(self.vector, q=self.q, name="d"),
        )

    @property
    def shape(self) -> tuple[int, ...]:
        return self.vector.shape


@dataclass(frozen=True, slots=True, eq=False)
class C2LakeUserSecret:
    """用户秘密值 d_i1 及其公开请求 P_i1。"""

    identity: bytes
    q: int
    profile: str
    backend: BackendName
    d_i1: ArrayI64
    p_i1: ArrayI64
    array_copy_policy: str = field(init=False, default="copy_and_mark_readonly")
    arrays_readonly: bool = field(init=False, default=True)

    def __post_init__(self) -> None:
        identity = _normalize_identity(self.identity)
        _validate_q(self.q)
        object.__setattr__(self, "identity", identity)
        object.__setattr__(self, "backend", _validate_backend(self.backend))
        object.__setattr__(self, "d_i1", _readonly_zq_vector(self.d_i1, q=self.q, name="d_i1"))
        object.__setattr__(self, "p_i1", _readonly_zq_vector(self.p_i1, q=self.q, name="P_i1"))
        _ensure_same_shape(self.d_i1, self.p_i1, "d_i1", "P_i1")

    @property
    def shape(self) -> tuple[int, ...]:
        return self.d_i1.shape


@dataclass(frozen=True, slots=True, eq=False)
class C2LakePartialPrivateKey:
    """KGC 生成的部分私钥 d_i0 与公开分量 P_i0。"""

    identity: bytes
    q: int
    profile: str
    backend: BackendName
    d_i0: ArrayI64
    p_i0: ArrayI64
    array_copy_policy: str = field(init=False, default="copy_and_mark_readonly")
    arrays_readonly: bool = field(init=False, default=True)

    def __post_init__(self) -> None:
        identity = _normalize_identity(self.identity)
        _validate_q(self.q)
        object.__setattr__(self, "identity", identity)
        object.__setattr__(self, "backend", _validate_backend(self.backend))
        object.__setattr__(self, "d_i0", _readonly_zq_vector(self.d_i0, q=self.q, name="d_i0"))
        object.__setattr__(self, "p_i0", _readonly_zq_vector(self.p_i0, q=self.q, name="P_i0"))
        _ensure_same_shape(self.d_i0, self.p_i0, "d_i0", "P_i0")

    @property
    def shape(self) -> tuple[int, ...]:
        return self.d_i0.shape


@dataclass(frozen=True, slots=True, eq=False)
class C2LakePublicKey:
    """用户公钥 pk_i=(P_i0,P_i1)。"""

    identity: bytes
    q: int
    profile: str
    backend: BackendName
    p_i0: ArrayI64
    p_i1: ArrayI64
    array_copy_policy: str = field(init=False, default="copy_and_mark_readonly")
    arrays_readonly: bool = field(init=False, default=True)

    def __post_init__(self) -> None:
        identity = _normalize_identity(self.identity)
        _validate_q(self.q)
        object.__setattr__(self, "identity", identity)
        object.__setattr__(self, "backend", _validate_backend(self.backend))
        object.__setattr__(self, "p_i0", _readonly_zq_vector(self.p_i0, q=self.q, name="P_i0"))
        object.__setattr__(self, "p_i1", _readonly_zq_vector(self.p_i1, q=self.q, name="P_i1"))
        _ensure_same_shape(self.p_i0, self.p_i1, "P_i0", "P_i1")

    @property
    def shape(self) -> tuple[int, ...]:
        return self.p_i0.shape


@dataclass(frozen=True, slots=True, eq=False)
class C2LakePrivateKey:
    """用户私钥 sk_i=(d_i0,d_i1)。"""

    identity: bytes
    q: int
    profile: str
    backend: BackendName
    d_i0: ArrayI64
    d_i1: ArrayI64
    array_copy_policy: str = field(init=False, default="copy_and_mark_readonly")
    arrays_readonly: bool = field(init=False, default=True)

    def __post_init__(self) -> None:
        identity = _normalize_identity(self.identity)
        _validate_q(self.q)
        object.__setattr__(self, "identity", identity)
        object.__setattr__(self, "backend", _validate_backend(self.backend))
        object.__setattr__(self, "d_i0", _readonly_zq_vector(self.d_i0, q=self.q, name="d_i0"))
        object.__setattr__(self, "d_i1", _readonly_zq_vector(self.d_i1, q=self.q, name="d_i1"))
        _ensure_same_shape(self.d_i0, self.d_i1, "d_i0", "d_i1")

    @property
    def shape(self) -> tuple[int, ...]:
        return self.d_i0.shape


@dataclass(frozen=True, slots=True, eq=False)
class C2LakeKeyPair:
    """用户完整密钥对，包含 q/profile/backend 与只读数组策略声明。"""

    identity: bytes
    q: int
    profile: str
    backend: BackendName
    private_key: C2LakePrivateKey
    public_key: C2LakePublicKey
    array_copy_policy: str = field(init=False, default="copy_and_mark_readonly")
    arrays_readonly: bool = field(init=False, default=True)

    def __post_init__(self) -> None:
        identity = _normalize_identity(self.identity)
        _validate_q(self.q)
        object.__setattr__(self, "identity", identity)
        object.__setattr__(self, "backend", _validate_backend(self.backend))
        _ensure_record_context(self, self.private_key, "private_key")
        _ensure_record_context(self, self.public_key, "public_key")
        if self.private_key.identity != identity or self.public_key.identity != identity:
            raise C2LakeCoreError("IDENTITY_ERROR", "密钥对 identity 不一致")
        _ensure_same_shape(
            self.private_key.d_i0,
            self.public_key.p_i0,
            "private_key.d_i0",
            "public_key.P_i0",
        )

    @property
    def shape(self) -> tuple[int, ...]:
        return self.private_key.shape


def load_c2lake_profile(name: str, *, specs_dir: Path | None = None) -> C2LakeProfile:
    """载入并校验 C2LAKE profile。"""

    try:
        raw = load_profile("c2lake", name, specs_dir=specs_dir)
    except ReproductionError as error:
        raise C2LakeCoreError("PROFILE_ERROR", str(error)) from error
    return _validate_profile_mapping(name, raw)


def setup(
    profile: str,
    *,
    seed: int,
    backend: str = "safe",
    specs_dir: Path | None = None,
) -> tuple[C2LakePublicParameters, C2LakeMasterSecret]:
    """执行 C2LAKE Setup，输出公共参数和 master secret。"""

    profile_record = load_c2lake_profile(profile, specs_dir=specs_dir)
    backend_name = _validate_backend(backend)
    rng = seeded_rng(seed)
    matrix = uniform_mod_q(rng, (profile_record.n, profile_record.n), profile_record.q)
    master_vector = bounded_ternary_vector(
        rng,
        profile_record.n,
        q=profile_record.q,
        beta=profile_record.beta,
    )
    public_key = vector_times_matrix(
        master_vector,
        matrix,
        q=profile_record.q,
        backend=backend_name,
    )
    public_params = C2LakePublicParameters(
        n=profile_record.n,
        q=profile_record.q,
        beta=profile_record.beta,
        profile=profile_record.name,
        family=profile_record.family,
        backend=backend_name,
        secret_sampling=profile_record.secret_sampling,
        matrix=matrix,
        public_key=public_key,
    )
    master_secret = C2LakeMasterSecret(
        q=profile_record.q,
        profile=profile_record.name,
        backend=backend_name,
        vector=master_vector,
    )
    return public_params, master_secret


def set_secret_value(
    public_params: C2LakePublicParameters,
    identity: object,
    *,
    seed: int,
) -> C2LakeUserSecret:
    """执行 SetSecretValue(ID_i)，生成 d_i1 与 P_i1。"""

    rng = seeded_rng(seed)
    identity_bytes = _normalize_identity(identity)
    d_i1 = _sample_user_vector(public_params, rng)
    p_i1 = vector_times_matrix(
        d_i1,
        public_params.matrix,
        q=public_params.q,
        backend=public_params.backend,
    )
    return C2LakeUserSecret(
        identity=identity_bytes,
        q=public_params.q,
        profile=public_params.profile,
        backend=public_params.backend,
        d_i1=d_i1,
        p_i1=p_i1,
    )


def extract_partial_private_key(
    public_params: C2LakePublicParameters,
    master_secret: C2LakeMasterSecret,
    identity: object,
    p_i1: npt.ArrayLike,
    *,
    seed: int,
) -> C2LakePartialPrivateKey:
    """执行 PartialPrivateKeyExtract(ID_i, P_i1)。"""

    _ensure_record_context(public_params, master_secret, "master_secret")
    identity_bytes = _normalize_identity(identity)
    p_i1_checked = _readonly_zq_vector(p_i1, n=public_params.n, q=public_params.q, name="P_i1")
    rng = seeded_rng(seed)
    r_i = _sample_kgc_randomness(public_params, rng)
    p_i0 = vector_times_matrix(
        r_i,
        public_params.matrix,
        q=public_params.q,
        backend=public_params.backend,
    )
    h1_i = public_params.hash_suite.h1(
        identity_bytes,
        p_i0,
        p_i1_checked,
        public_params.public_key,
        q=public_params.q,
    )
    d_i0 = zq_add(
        r_i,
        zq_scalar_mul(h1_i, master_secret.vector, q=public_params.q),
        q=public_params.q,
    )
    return C2LakePartialPrivateKey(
        identity=identity_bytes,
        q=public_params.q,
        profile=public_params.profile,
        backend=public_params.backend,
        d_i0=d_i0,
        p_i0=p_i0,
    )


def verify_partial_key(
    public_params: C2LakePublicParameters,
    identity: object,
    user_secret: C2LakeUserSecret,
    partial_key: C2LakePartialPrivateKey,
) -> bool:
    """验证 d_i0^T M == P_i0 + H1(ID_i,P_i0,P_i1,P)P mod q。"""

    _ensure_record_context(public_params, user_secret, "user_secret")
    _ensure_record_context(public_params, partial_key, "partial_key")
    identity_bytes = _normalize_identity(identity)
    if identity_bytes != user_secret.identity or identity_bytes != partial_key.identity:
        return False
    if user_secret.shape != (public_params.n,) or partial_key.shape != (public_params.n,):
        raise C2LakeCoreError("SHAPE_ERROR", "用户秘密或部分私钥 shape 与公共参数不一致")

    h1_i = public_params.hash_suite.h1(
        identity_bytes,
        partial_key.p_i0,
        user_secret.p_i1,
        public_params.public_key,
        q=public_params.q,
    )
    lhs = vector_times_matrix(
        partial_key.d_i0,
        public_params.matrix,
        q=public_params.q,
        backend=public_params.backend,
    )
    rhs = zq_add(
        partial_key.p_i0,
        zq_scalar_mul(h1_i, public_params.public_key, q=public_params.q),
        q=public_params.q,
    )
    return bool(np.array_equal(lhs, rhs))


def verify_and_assemble_key(
    public_params: C2LakePublicParameters,
    identity: object,
    user_secret: C2LakeUserSecret,
    partial_key: C2LakePartialPrivateKey,
) -> C2LakeKeyPair:
    """验证部分私钥，成功后组装 sk_i=(d_i0,d_i1)、pk_i=(P_i0,P_i1)。"""

    if not verify_partial_key(public_params, identity, user_secret, partial_key):
        raise C2LakeCoreError("INVALID_PARTIAL_KEY", "部分私钥验证式不成立")
    identity_bytes = _normalize_identity(identity)
    private_key = C2LakePrivateKey(
        identity=identity_bytes,
        q=public_params.q,
        profile=public_params.profile,
        backend=public_params.backend,
        d_i0=partial_key.d_i0,
        d_i1=user_secret.d_i1,
    )
    public_key = C2LakePublicKey(
        identity=identity_bytes,
        q=public_params.q,
        profile=public_params.profile,
        backend=public_params.backend,
        p_i0=partial_key.p_i0,
        p_i1=user_secret.p_i1,
    )
    return C2LakeKeyPair(
        identity=identity_bytes,
        q=public_params.q,
        profile=public_params.profile,
        backend=public_params.backend,
        private_key=private_key,
        public_key=public_key,
    )


def uniform_mod_q(
    rng: np.random.Generator,
    shape: int | tuple[int, ...],
    q: int,
) -> ArrayI64:
    """从 [0,q-1] 均匀采样；PCG64 仅用于可重复实验。"""

    _validate_q(q)
    sample_shape = (shape,) if isinstance(shape, int) else shape
    if not sample_shape or any(not isinstance(size, int) or size <= 0 for size in sample_shape):
        raise C2LakeCoreError("SHAPE_ERROR", "采样 shape 必须为正整数维度")
    values = rng.integers(0, q, size=sample_shape, dtype=np.int64)
    values.setflags(write=False)
    return values


def bounded_ternary_vector(
    rng: np.random.Generator,
    n: int,
    *,
    q: int,
    beta: float,
    max_attempts: int = 10_000,
) -> ArrayI64:
    """从 {-1,0,1} 拒绝采样，按 centered norm<=beta 验证后映射到 Zq。"""

    _validate_positive_int(n, "n", code="SHAPE_ERROR")
    _validate_q(q)
    _validate_positive_number(beta, "beta", code="PROFILE_ERROR")
    for _ in range(max_attempts):
        centered = rng.integers(-1, 2, size=n, dtype=np.int64)
        if not np.any(centered):
            continue
        norm = float(np.linalg.norm(centered.astype(np.float64)))
        if norm <= beta:
            mapped = np.remainder(centered, q).astype(np.int64)
            result = mapped
            result.setflags(write=False)
            return result
    raise C2LakeCoreError("SAMPLER_ERROR", "bounded_ternary 拒绝采样超过最大次数")


def centered_representative(vector: npt.ArrayLike, *, q: int) -> ArrayI64:
    """将 Zq 向量转换为 centered representative。"""

    values = _readonly_zq_vector(vector, q=q, name="vector")
    centered = values.copy()
    threshold = q // 2
    centered[centered > threshold] -= q
    centered.setflags(write=False)
    return centered


def centered_norm(vector: npt.ArrayLike, *, q: int) -> float:
    """计算 Zq 向量的 centered 欧氏范数。"""

    centered = centered_representative(vector, q=q)
    return float(np.linalg.norm(centered.astype(np.float64)))


def vector_times_matrix(
    vector: npt.ArrayLike,
    matrix: npt.ArrayLike,
    *,
    q: int,
    backend: str = "safe",
) -> ArrayI64:
    """计算 v^T M mod q，返回长度 n 的一维数组。"""

    backend_name = _validate_backend(backend)
    _validate_q(q)
    checked_matrix = _readonly_zq_matrix(matrix, q=q, name="M")
    checked_vector = _readonly_zq_vector(
        vector,
        n=checked_matrix.shape[0],
        q=q,
        name="vector",
    )
    if checked_matrix.shape[0] != checked_matrix.shape[1]:
        raise C2LakeCoreError("SHAPE_ERROR", "vector_times_matrix 要求 M 为方阵")
    result = _matmul_checked(checked_vector, checked_matrix, q=q, backend=backend_name)
    result.setflags(write=False)
    return result


def matrix_times_vector(
    matrix: npt.ArrayLike,
    vector: npt.ArrayLike,
    *,
    q: int,
    backend: str = "safe",
) -> ArrayI64:
    """计算 M v mod q，返回长度 n 的一维数组。"""

    backend_name = _validate_backend(backend)
    _validate_q(q)
    checked_matrix = _readonly_zq_matrix(matrix, q=q, name="M")
    checked_vector = _readonly_zq_vector(
        vector,
        n=checked_matrix.shape[1],
        q=q,
        name="vector",
    )
    if checked_matrix.shape[0] != checked_matrix.shape[1]:
        raise C2LakeCoreError("SHAPE_ERROR", "matrix_times_vector 要求 M 为方阵")
    result = _matmul_checked(checked_matrix, checked_vector, q=q, backend=backend_name)
    result.setflags(write=False)
    return result


def dot_mod(left: npt.ArrayLike, right: npt.ArrayLike, *, q: int, backend: str = "safe") -> int:
    """计算两个 Zq 向量点积 mod q。"""

    backend_name = _validate_backend(backend)
    _validate_q(q)
    left_vector = _readonly_zq_vector(left, q=q, name="left")
    right_vector = _readonly_zq_vector(right, n=left_vector.shape[0], q=q, name="right")
    if backend_name == "fast":
        _ensure_int64_accumulator_safe(left_vector.shape[0], q)
        return int(np.dot(left_vector, right_vector) % q)
    if _int64_accumulator_is_safe(left_vector.shape[0], q):
        return int(np.dot(left_vector, right_vector) % q)
    total = sum(int(a) * int(b) for a, b in zip(left_vector, right_vector, strict=True))
    return total % q


def zq_add(left: npt.ArrayLike, right: npt.ArrayLike, *, q: int) -> ArrayI64:
    """计算两个同 shape Zq 数组逐元素相加 mod q。"""

    _validate_q(q)
    left_array = _readonly_zq_array(left, q=q, name="left")
    right_array = _readonly_zq_array(right, q=q, name="right")
    _ensure_same_shape(left_array, right_array, "left", "right")
    result = np.remainder(left_array + right_array, q).astype(np.int64)
    output = cast(ArrayI64, result)
    output.setflags(write=False)
    return output


def zq_scalar_mul(scalar: int, value: npt.ArrayLike, *, q: int) -> ArrayI64:
    """计算 scalar * value mod q。"""

    checked_scalar = _validate_zq_scalar(scalar, q, name="scalar")
    value_array = _readonly_zq_array(value, q=q, name="value")
    result = np.remainder(checked_scalar * value_array, q).astype(np.int64)
    output = result
    output.setflags(write=False)
    return output


def encode_zq_array(value: npt.ArrayLike, *, q: int, name: str = "array") -> bytes:
    """公开数组编码 helper；编码包含 shape、q 和 row-major payload。"""

    array = _readonly_zq_array(value, q=q, name=name)
    if array.ndim == 1:
        return _encode_vector(name, array, q=q)
    if array.ndim == 2:
        return _encode_matrix(name, array, q=q)
    raise C2LakeCoreError("SHAPE_ERROR", f"{name} 只能是一维向量或二维矩阵")


def _sample_user_vector(
    public_params: C2LakePublicParameters,
    rng: np.random.Generator,
) -> ArrayI64:
    if public_params.family == "paper_literal" and public_params.secret_sampling == "literal":
        return uniform_mod_q(rng, public_params.n, public_params.q)
    return bounded_ternary_vector(rng, public_params.n, q=public_params.q, beta=public_params.beta)


def _sample_kgc_randomness(
    public_params: C2LakePublicParameters,
    rng: np.random.Generator,
) -> ArrayI64:
    if public_params.family == "paper_literal" and public_params.secret_sampling == "literal":
        return uniform_mod_q(rng, public_params.n, public_params.q)
    return bounded_ternary_vector(rng, public_params.n, q=public_params.q, beta=public_params.beta)


def _validate_profile_mapping(name: str, raw: dict[str, object]) -> C2LakeProfile:
    family = _require_profile_str(raw, "family")
    matrix_shape = _require_profile_str(raw, "matrix_shape")
    secret_sampling = _require_profile_str(raw, "secret_sampling")
    m = _require_profile_positive_int(raw, "m")
    n = _require_profile_positive_int(raw, "n")
    q = _require_profile_positive_int(raw, "q")
    beta = _require_profile_positive_number(raw, "beta")
    q_must_be_prime = _require_profile_bool(raw, "q_must_be_prime")
    if family not in _ALLOWED_FAMILIES:
        raise C2LakeCoreError("PROFILE_ERROR", f"profile family {family!r} 不合法")
    if matrix_shape not in _ALLOWED_MATRIX_SHAPES:
        raise C2LakeCoreError("PROFILE_ERROR", f"matrix_shape {matrix_shape!r} 不合法")
    if secret_sampling not in _ALLOWED_SECRET_SAMPLING:
        raise C2LakeCoreError("PROFILE_ERROR", f"secret_sampling {secret_sampling!r} 不合法")
    if family in {"audited", "audited_prime"} and not q_must_be_prime:
        raise C2LakeCoreError(
            "PROFILE_ERROR",
            "audited/audited_prime profile 必须设置 q_must_be_prime=true",
        )
    if q_must_be_prime and not _is_prime(q):
        raise C2LakeCoreError("PROFILE_ERROR", "q_must_be_prime=true 但 q 不是素数")
    return C2LakeProfile(
        name=name,
        family=family,
        m=m,
        n=n,
        q=q,
        beta=beta,
        q_must_be_prime=q_must_be_prime,
        matrix_shape=matrix_shape,
        secret_sampling=secret_sampling,
    )


def _require_profile_str(raw: dict[str, object], field_name: str) -> str:
    value = raw.get(field_name)
    if isinstance(value, str) and value:
        return value
    raise C2LakeCoreError("PROFILE_ERROR", f"profile 字段 {field_name!r} 必须是非空字符串")


def _require_profile_positive_int(raw: dict[str, object], field_name: str) -> int:
    value = raw.get(field_name)
    if type(value) is int and value > 0:
        return value
    raise C2LakeCoreError("PROFILE_ERROR", f"profile 字段 {field_name!r} 必须是正整数")


def _require_profile_positive_number(raw: dict[str, object], field_name: str) -> float:
    value = raw.get(field_name)
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
        return float(value)
    raise C2LakeCoreError("PROFILE_ERROR", f"profile 字段 {field_name!r} 必须是正数")


def _require_profile_bool(raw: dict[str, object], field_name: str) -> bool:
    value = raw.get(field_name)
    if type(value) is bool:
        return value
    raise C2LakeCoreError("PROFILE_ERROR", f"profile 字段 {field_name!r} 必须是布尔值")


def _readonly_zq_vector(
    value: npt.ArrayLike,
    *,
    q: int,
    name: str,
    n: int | None = None,
) -> ArrayI64:
    array = _readonly_zq_array(value, q=q, name=name)
    if array.ndim != 1:
        raise C2LakeCoreError("SHAPE_ERROR", f"{name} 必须是一维向量")
    if n is not None and array.shape != (n,):
        raise C2LakeCoreError("SHAPE_ERROR", f"{name} shape 必须为 ({n},)")
    return array


def _readonly_zq_matrix(
    value: npt.ArrayLike,
    *,
    q: int,
    name: str,
    n: int | None = None,
) -> ArrayI64:
    array = _readonly_zq_array(value, q=q, name=name)
    if array.ndim != 2:
        raise C2LakeCoreError("SHAPE_ERROR", f"{name} 必须是二维矩阵")
    if n is not None and array.shape != (n, n):
        raise C2LakeCoreError("SHAPE_ERROR", f"{name} shape 必须为 ({n}, {n})")
    return array


def _readonly_zq_array(value: npt.ArrayLike, *, q: int, name: str) -> ArrayI64:
    _validate_q(q)
    raw = np.asarray(value)
    if raw.dtype == np.dtype(bool) or not np.issubdtype(raw.dtype, np.integer):
        raise C2LakeCoreError("DTYPE_ERROR", f"{name} dtype 必须为整数")
    array = cast(ArrayI64, np.array(raw, dtype=np.int64, copy=True))
    if np.any(array < 0) or np.any(array >= q):
        raise C2LakeCoreError("DOMAIN_ERROR", f"{name} 元素必须位于 [0,q-1]")
    array.setflags(write=False)
    return array


def _validate_zq_scalar(value: int, q: int, *, name: str) -> int:
    _validate_q(q)
    if isinstance(value, bool) or not isinstance(value, int):
        raise C2LakeCoreError("DTYPE_ERROR", f"{name} 必须是整数")
    if value < 0 or value >= q:
        raise C2LakeCoreError("DOMAIN_ERROR", f"{name} 必须位于 [0,q-1]")
    return value


def _matmul_checked(
    left: ArrayI64,
    right: ArrayI64,
    *,
    q: int,
    backend: BackendName,
) -> ArrayI64:
    common_dimension = _matmul_common_dimension(left, right)
    if backend == "fast":
        _ensure_int64_accumulator_safe(common_dimension, q)
        result = np.matmul(left, right) % q
        return cast(ArrayI64, np.asarray(result, dtype=np.int64))
    if _int64_accumulator_is_safe(common_dimension, q):
        result = np.matmul(left, right) % q
        return cast(ArrayI64, np.asarray(result, dtype=np.int64))
    return _python_int_matmul(left, right, q=q)


def _matmul_common_dimension(left: ArrayI64, right: ArrayI64) -> int:
    if left.ndim == 1 and right.ndim == 2:
        if left.shape[0] != right.shape[0]:
            raise C2LakeCoreError("SHAPE_ERROR", "vector_times_matrix 维度不匹配")
        return left.shape[0]
    if left.ndim == 2 and right.ndim == 1:
        if left.shape[1] != right.shape[0]:
            raise C2LakeCoreError("SHAPE_ERROR", "matrix_times_vector 维度不匹配")
        return left.shape[1]
    raise C2LakeCoreError("SHAPE_ERROR", "只支持 vector×matrix 或 matrix×vector")


def _python_int_matmul(left: ArrayI64, right: ArrayI64, *, q: int) -> ArrayI64:
    if left.ndim == 1 and right.ndim == 2:
        columns = right.shape[1]
        values = [
            sum(int(left[row]) * int(right[row, column]) for row in range(left.shape[0])) % q
            for column in range(columns)
        ]
        return cast(ArrayI64, np.array(values, dtype=np.int64))
    rows = left.shape[0]
    values = [
        sum(int(left[row, column]) * int(right[column]) for column in range(right.shape[0])) % q
        for row in range(rows)
    ]
    return cast(ArrayI64, np.array(values, dtype=np.int64))


def _int64_accumulator_is_safe(length: int, q: int) -> bool:
    return length * (q - 1) * (q - 1) <= _MAX_INT64


def _ensure_int64_accumulator_safe(length: int, q: int) -> None:
    if not _int64_accumulator_is_safe(length, q):
        raise C2LakeCoreError(
            "BACKEND_OVERFLOW_UNSAFE",
            "fast backend 的最坏累加范围超过 int64",
        )


def _validate_backend(backend: str) -> BackendName:
    if backend not in _ALLOWED_BACKENDS:
        raise C2LakeCoreError("BACKEND_ERROR", f"非法 backend {backend!r}")
    return cast(BackendName, backend)


def _validate_q(q: int) -> None:
    _validate_positive_int(q, "q", code="MODULUS_ERROR")
    if q < 2:
        raise C2LakeCoreError("MODULUS_ERROR", "q 必须大于等于 2")


def _validate_positive_int(value: int, name: str, *, code: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise C2LakeCoreError(code, f"{name} 必须是正整数")


def _validate_positive_number(value: float, name: str, *, code: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise C2LakeCoreError(code, f"{name} 必须是正数")


def _ensure_same_shape(
    left: ArrayI64,
    right: ArrayI64,
    left_name: str,
    right_name: str,
) -> None:
    if left.shape != right.shape:
        raise C2LakeCoreError(
            "SHAPE_ERROR",
            f"{left_name} shape {left.shape} 与 {right_name} shape {right.shape} 不一致",
        )


def _ensure_record_context(
    expected: C2LakePublicParameters | C2LakeKeyPair,
    actual: C2LakeMasterSecret
    | C2LakeUserSecret
    | C2LakePartialPrivateKey
    | C2LakePublicKey
    | C2LakePrivateKey,
    name: str,
) -> None:
    if actual.q != expected.q:
        raise C2LakeCoreError("MODULUS_ERROR", f"{name} q 与上下文不一致")
    if actual.profile != expected.profile:
        raise C2LakeCoreError("PROFILE_ERROR", f"{name} profile 与上下文不一致")
    if actual.backend != expected.backend:
        raise C2LakeCoreError("BACKEND_ERROR", f"{name} backend 与上下文不一致")


def _normalize_identity(identity: object) -> bytes:
    if isinstance(identity, str) and identity:
        return identity.encode("utf-8")
    if isinstance(identity, bytes) and identity:
        return bytes(bytearray(identity))
    raise C2LakeCoreError("IDENTITY_ERROR", "identity 必须是非空 bytes 或 str")


def _encode_field(type_tag: str, payload: bytes) -> bytes:
    tag = type_tag.encode("ascii")
    return tag + len(payload).to_bytes(8, "big") + payload


def _encode_bytes(type_tag: str, payload: bytes) -> bytes:
    return _encode_field(type_tag, payload)


def _encode_identity(identity: object) -> bytes:
    return _encode_field("identity", _normalize_identity(identity))


def _encode_uint(type_tag: str, value: int) -> bytes:
    return _encode_field(type_tag, value.to_bytes(max(1, (value.bit_length() + 7) // 8), "big"))


def _encode_timestamp(timestamp: int | bytes | str) -> bytes:
    if isinstance(timestamp, int) and not isinstance(timestamp, bool) and timestamp >= 0:
        return _encode_uint("timestamp", timestamp)
    if isinstance(timestamp, str):
        return _encode_field("timestamp", timestamp.encode("utf-8"))
    if isinstance(timestamp, bytes) and timestamp:
        return _encode_field("timestamp", bytes(timestamp))
    raise C2LakeCoreError("DTYPE_ERROR", "timestamp 必须是非负整数、非空 bytes 或 str")


def _encode_vector(type_tag: str, value: npt.ArrayLike, *, q: int) -> bytes:
    vector = _readonly_zq_vector(value, q=q, name=type_tag)
    shape_payload = b"".join(
        (
            len(vector.shape).to_bytes(8, "big"),
            vector.shape[0].to_bytes(8, "big"),
            q.to_bytes(8, "big"),
        )
    )
    data_payload = vector.astype(">i8", copy=False).tobytes(order="C")
    return _encode_field(f"vector:{type_tag}", shape_payload + data_payload)


def _encode_matrix(type_tag: str, value: npt.ArrayLike, *, q: int) -> bytes:
    matrix = _readonly_zq_matrix(value, q=q, name=type_tag)
    rows, columns = matrix.shape
    shape_payload = b"".join(
        (
            len(matrix.shape).to_bytes(8, "big"),
            rows.to_bytes(8, "big"),
            columns.to_bytes(8, "big"),
            q.to_bytes(8, "big"),
        )
    )
    data_payload = matrix.astype(">i8", copy=False).tobytes(order="C")
    return _encode_field(f"matrix:{type_tag}", shape_payload + data_payload)


def _shake_to_zq_star(payload: bytes, q: int) -> int:
    _validate_q(q)
    byte_length = max(1, (q.bit_length() + 7) // 8)
    counter = 0
    while True:
        shake = hashlib.shake_256()
        shake.update(payload)
        shake.update(counter.to_bytes(8, "big"))
        candidate = int.from_bytes(shake.digest(byte_length), "big")
        if 1 <= candidate <= q - 1:
            return candidate
        counter += 1


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value in {2, 3}:
        return True
    if value % 2 == 0:
        return False
    limit = math.isqrt(value)
    candidate = 3
    while candidate <= limit:
        if value % candidate == 0:
            return False
        candidate += 2
    return True


__all__ = [
    "BackendName",
    "C2LakeCoreError",
    "C2LakeHashSuite",
    "C2LakeKeyPair",
    "C2LakeMasterSecret",
    "C2LakePartialPrivateKey",
    "C2LakePrivateKey",
    "C2LakeProfile",
    "C2LakePublicKey",
    "C2LakePublicParameters",
    "C2LakeUserSecret",
    "bounded_ternary_vector",
    "centered_norm",
    "centered_representative",
    "dot_mod",
    "encode_zq_array",
    "extract_partial_private_key",
    "load_c2lake_profile",
    "matrix_times_vector",
    "set_secret_value",
    "setup",
    "uniform_mod_q",
    "vector_times_matrix",
    "verify_and_assemble_key",
    "verify_partial_key",
    "zq_add",
    "zq_scalar_mul",
]
