"""LCLA-AKA 的 SHAKE256、长度前缀编码和域分离接口。"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

import numpy as np
import numpy.typing as npt

from lattice_aka_repro.lcla_modular import pack_bits
from lattice_aka_repro.lcla_types import (
    IntArray,
    LCLAError,
    LCLAProfile,
    freeze_integer_array,
)


def normalize_identity(identity: str | bytes) -> bytes:
    """规范化非空 str/bytes identity。"""

    if isinstance(identity, str):
        encoded = identity.encode("utf-8")
    elif isinstance(identity, bytes):
        encoded = memoryview(identity).tobytes()
    else:
        raise LCLAError("IDENTITY_ERROR", "identity 必须为非空 str 或 bytes")
    if not encoded:
        raise LCLAError("IDENTITY_ERROR", "identity 不能为空")
    return encoded


def _length_prefix(value: bytes) -> bytes:
    return len(value).to_bytes(8, "big") + value


def _typed_field(tag: str, value: bytes) -> bytes:
    return _length_prefix(tag.encode("ascii")) + _length_prefix(value)


def encode_zq_array(
    value: npt.ArrayLike,
    *,
    q: int,
    profile_version: str,
    tag: str,
) -> bytes:
    """编码 type、shape、q、profile 版本和 row-major 数据。"""

    array = np.asarray(value)
    if not np.issubdtype(array.dtype, np.integer):
        raise LCLAError("DTYPE_ERROR", f"{tag} 必须为整数数组")
    normalized = np.asarray(array, dtype=np.int64)
    if np.any(normalized < 0) or np.any(normalized >= q):
        raise LCLAError("DOMAIN_ERROR", f"{tag} 必须属于 Zq")
    shape = len(normalized.shape).to_bytes(4, "big") + b"".join(
        dimension.to_bytes(8, "big") for dimension in normalized.shape
    )
    payload = b"".join(
        (
            _typed_field("profile", profile_version.encode("utf-8")),
            _typed_field("q", q.to_bytes(max(1, (q.bit_length() + 7) // 8), "big")),
            _typed_field("shape", shape),
            _typed_field("dtype", b"unsigned-zq"),
            _typed_field(
                "data",
                b"".join(
                    int(item).to_bytes(max(1, (q.bit_length() + 7) // 8), "big")
                    for item in normalized.flat
                ),
            ),
        )
    )
    return _typed_field(tag, payload)


def encode_bit_array(value: npt.ArrayLike, *, profile_version: str, tag: str) -> bytes:
    """编码 bit vector 的 shape 与精确位长。"""

    array = np.asarray(value)
    if array.ndim != 1 or not np.issubdtype(array.dtype, np.integer):
        raise LCLAError("ENCODING_ERROR", f"{tag} 必须为一维 bit vector")
    bits = np.asarray(array, dtype=np.int64)
    if np.any((bits != 0) & (bits != 1)):
        raise LCLAError("DOMAIN_ERROR", f"{tag} 必须属于 {{0,1}}")
    payload = b"".join(
        (
            _typed_field("profile", profile_version.encode("utf-8")),
            _typed_field("bit_length", len(bits).to_bytes(8, "big")),
            _typed_field("data", pack_bits(bits)),
        )
    )
    return _typed_field(tag, payload)


def _shake_bits(domain: bytes, payload: bytes, bit_length: int) -> IntArray:
    if bit_length <= 0:
        raise LCLAError("HASH_ERROR", "bit_length 必须为正")
    data = hashlib.shake_256(_length_prefix(domain) + payload).digest((bit_length + 7) // 8)
    unpacked = np.unpackbits(np.frombuffer(data, dtype=np.uint8), bitorder="little")
    return np.asarray(unpacked[:bit_length], dtype=np.int64)


@dataclass(frozen=True, slots=True)
class LCLAHashSuite:
    """H1 注册表及 H2 分域接口。"""

    profile: LCLAProfile
    programmed: bool
    _registry: dict[bytes, IntArray] = field(default_factory=dict, repr=False, compare=False)

    def register_h1(self, identity: str | bytes, pk_full: npt.ArrayLike) -> None:
        """constructed backend 将 identity 绑定到构造的 pk_full。"""

        if not self.programmed:
            raise LCLAError("H1_BINDING_ERROR", "非 programmed H1 不允许注册")
        identity_bytes = normalize_identity(identity)
        value = freeze_integer_array(
            pk_full,
            shape=(self.profile.n,),
            q=self.profile.q,
            name="pk_full",
        )
        previous = self._registry.get(identity_bytes)
        if previous is not None and not np.array_equal(previous, value):
            raise LCLAError("H1_BINDING_ERROR", "同一 identity 不能冲突注册")
        self._registry[identity_bytes] = value

    def has_registered_identity(self, identity: str | bytes) -> bool:
        """检查 programmed registry 是否包含 identity。"""

        return normalize_identity(identity) in self._registry

    def h1(self, identity: str | bytes) -> IntArray:
        """H1: identity -> Zq^n。"""

        identity_bytes = normalize_identity(identity)
        registered = self._registry.get(identity_bytes)
        if registered is not None:
            return np.array(registered, dtype=np.int64, copy=True)
        if self.programmed:
            raise LCLAError("H1_BINDING_ERROR", "constructed H1 identity 未注册")
        payload = b"".join(
            (
                _typed_field("profile", self.profile.name.encode("utf-8")),
                _typed_field("identity", identity_bytes),
                _typed_field("q", self.profile.q.to_bytes(8, "big")),
                _typed_field("n", self.profile.n.to_bytes(8, "big")),
            )
        )
        raw = hashlib.shake_256(_length_prefix(b"LCLA-H1-v1") + payload).digest(self.profile.n * 8)
        return np.asarray(
            [
                int.from_bytes(raw[index : index + 8], "big") % self.profile.q
                for index in range(0, len(raw), 8)
            ],
            dtype=np.int64,
        )

    def mac_a(self, c_a: npt.ArrayLike, m1: npt.ArrayLike, delta_a: npt.ArrayLike) -> IntArray:
        """LCLA-MAC-A-v1，输出 m bits。"""

        payload = b"".join(
            (
                encode_zq_array(
                    c_a,
                    q=self.profile.q,
                    profile_version=self.profile.name,
                    tag="C_A",
                ),
                encode_bit_array(m1, profile_version=self.profile.name, tag="m1"),
                encode_bit_array(delta_a, profile_version=self.profile.name, tag="delta_A"),
            )
        )
        return _shake_bits(b"LCLA-MAC-A-v1", payload, self.profile.m)

    def mac_b(self, c_b: npt.ArrayLike, m1: npt.ArrayLike) -> IntArray:
        """LCLA-MAC-B-v1，输出 m bits。"""

        payload = b"".join(
            (
                encode_zq_array(
                    c_b,
                    q=self.profile.q,
                    profile_version=self.profile.name,
                    tag="C_B",
                ),
                encode_bit_array(m1, profile_version=self.profile.name, tag="m1"),
            )
        )
        return _shake_bits(b"LCLA-MAC-B-v1", payload, self.profile.m)

    def identity_mask(
        self,
        delta_b: npt.ArrayLike,
        h_a: npt.ArrayLike,
        c_b: npt.ArrayLike,
        m1: npt.ArrayLike,
        *,
        output_length: int,
    ) -> bytes:
        """LCLA-ID-MASK-v1，输出长度严格等于 identity 字节长度。"""

        if output_length <= 0:
            raise LCLAError("IDENTITY_ERROR", "identity mask 长度必须为正")
        payload = b"".join(
            (
                encode_bit_array(delta_b, profile_version=self.profile.name, tag="delta_B"),
                encode_bit_array(h_a, profile_version=self.profile.name, tag="h_A"),
                encode_zq_array(
                    c_b,
                    q=self.profile.q,
                    profile_version=self.profile.name,
                    tag="C_B",
                ),
                encode_bit_array(m1, profile_version=self.profile.name, tag="m1"),
                _typed_field("output_length", output_length.to_bytes(8, "big")),
            )
        )
        return hashlib.shake_256(_length_prefix(b"LCLA-ID-MASK-v1") + payload).digest(output_length)

    def session_key(
        self,
        identity_a: str | bytes,
        identity_b: str | bytes,
        m1: npt.ArrayLike,
        m2: npt.ArrayLike,
    ) -> tuple[bytes, bytes | None]:
        """论文 m-bit key，并为 audited profile 额外导出 32 bytes。"""

        payload = b"".join(
            (
                _typed_field("ID_A", normalize_identity(identity_a)),
                _typed_field("ID_B", normalize_identity(identity_b)),
                encode_bit_array(m1, profile_version=self.profile.name, tag="m1"),
                encode_bit_array(m2, profile_version=self.profile.name, tag="m2"),
            )
        )
        literal_bits = _shake_bits(b"LCLA-SESSION-KDF-v1", payload, self.profile.m)
        literal = pack_bits(literal_bits)
        audited = None
        if self.profile.family == "audited":
            audited = hashlib.shake_256(
                _length_prefix(b"LCLA-SESSION-KDF-AUDITED-v1") + payload
            ).digest(32)
        return literal, audited


def xor_identity(identity: bytes, mask: bytes) -> bytes:
    """等长 XOR。"""

    if not identity or len(identity) != len(mask):
        raise LCLAError("ENCODING_ERROR", "identity 与 mask 必须非空且等长")
    return bytes(left ^ right for left, right in zip(identity, mask, strict=True))


def transcript_hash(
    *,
    request_c_a: npt.ArrayLike,
    request_delta_a: npt.ArrayLike,
    request_h_a: npt.ArrayLike,
    response_c_b: npt.ArrayLike,
    response_h_b: npt.ArrayLike,
    finish_t_a: bytes,
    finish_delta_b: npt.ArrayLike,
    profile: LCLAProfile,
) -> bytes:
    """三轮、七字段 canonical transcript hash。"""

    payload = b"".join(
        (
            encode_zq_array(request_c_a, q=profile.q, profile_version=profile.name, tag="C_A"),
            encode_bit_array(request_delta_a, profile_version=profile.name, tag="delta_A"),
            encode_bit_array(request_h_a, profile_version=profile.name, tag="h_A"),
            encode_zq_array(response_c_b, q=profile.q, profile_version=profile.name, tag="C_B"),
            encode_bit_array(response_h_b, profile_version=profile.name, tag="h_B"),
            _typed_field("T_A", bytes(finish_t_a)),
            encode_bit_array(finish_delta_b, profile_version=profile.name, tag="delta_B"),
        )
    )
    return hashlib.shake_256(_length_prefix(b"LCLA-TRANSCRIPT-v1") + payload).digest(32)
