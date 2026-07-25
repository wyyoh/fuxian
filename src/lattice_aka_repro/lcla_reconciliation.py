"""LCLA-AKA Definition 5 的 S/Mod2 reconciliation。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from lattice_aka_repro.lcla_modular import centered_representative
from lattice_aka_repro.lcla_types import IntArray, LCLAError, freeze_integer_array


@dataclass(frozen=True, slots=True)
class LCLASignal:
    """公开 hint delta 与生成它的本地随机 b。"""

    delta: IntArray
    random_bits: IntArray
    q: int

    def __post_init__(self) -> None:
        m = int(np.asarray(self.delta).size)
        object.__setattr__(
            self,
            "delta",
            freeze_integer_array(self.delta, shape=(m,), bits=True, name="delta"),
        )
        object.__setattr__(
            self,
            "random_bits",
            freeze_integer_array(
                self.random_bits, shape=(m,), bits=True, name="signal random bits"
            ),
        )


def _validate_q(q: int) -> None:
    if isinstance(q, bool) or not isinstance(q, int) or q <= 2 or q % 2 == 0:
        raise LCLAError("MODULUS_ERROR", "Definition 5 要求奇数 q>2")


def mu_0(value: int, *, q: int) -> int:
    """论文式 (1)：在 [-floor(q/4), floor(q/4)] 内输出 0。"""

    _validate_q(q)
    centered = int(centered_representative(np.asarray([value]), q=q)[0])
    quarter = q // 4
    return 0 if -quarter <= centered <= quarter else 1


def mu_1(value: int, *, q: int) -> int:
    """论文式 (2)：在 [-floor(q/4)+1, floor(q/4)+1] 内输出 0。"""

    _validate_q(q)
    centered = int(centered_representative(np.asarray([value]), q=q)[0])
    quarter = q // 4
    return 0 if -quarter + 1 <= centered <= quarter + 1 else 1


def signal(
    value: npt.ArrayLike,
    *,
    q: int,
    seed: int,
) -> LCLASignal:
    """逐坐标随机选择 b，并输出 delta=S(x)=mu_b(x)。"""

    _validate_q(q)
    array = np.asarray(value)
    if array.ndim != 1 or not np.issubdtype(array.dtype, np.integer):
        raise LCLAError("SHAPE_ERROR", "signal 输入必须是一维整数向量")
    if np.any(array < 0) or np.any(array >= q):
        raise LCLAError("DOMAIN_ERROR", "signal 输入必须属于 Zq")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise LCLAError("SAMPLER_ERROR", "signal seed 必须为非负整数")
    rng = np.random.Generator(np.random.PCG64(seed))
    random_bits = np.asarray(rng.integers(0, 2, size=array.shape), dtype=np.int64)
    delta = np.asarray(
        [
            mu_0(int(item), q=q) if int(bit) == 0 else mu_1(int(item), q=q)
            for item, bit in zip(array, random_bits, strict=True)
        ],
        dtype=np.int64,
    )
    return LCLASignal(delta=delta, random_bits=random_bits, q=q)


def mod2(value: npt.ArrayLike, delta: npt.ArrayLike, *, q: int) -> IntArray:
    """论文 Definition 5 robust extractor。"""

    _validate_q(q)
    value_array = np.asarray(value)
    delta_array = np.asarray(delta)
    if value_array.ndim != 1 or delta_array.ndim != 1 or value_array.shape != delta_array.shape:
        raise LCLAError("SHAPE_ERROR", "Mod2 的 value/delta 必须为同 shape 一维向量")
    if not np.issubdtype(value_array.dtype, np.integer) or not np.issubdtype(
        delta_array.dtype, np.integer
    ):
        raise LCLAError("DTYPE_ERROR", "Mod2 输入必须为整数")
    if np.any(value_array < 0) or np.any(value_array >= q):
        raise LCLAError("DOMAIN_ERROR", "Mod2 value 必须属于 Zq")
    if np.any((delta_array != 0) & (delta_array != 1)):
        raise LCLAError("DOMAIN_ERROR", "Mod2 delta 必须属于 {0,1}")
    half = (q - 1) // 2
    return np.asarray(
        [
            ((int(item) + int(hint) * half) % q) % 2
            for item, hint in zip(value_array, delta_array, strict=True)
        ],
        dtype=np.int64,
    )


def lemma3_error_bound(q: int) -> float:
    """论文 Lemma 3 的 ||e|| < q/8 - 1 阈值。"""

    _validate_q(q)
    return q / 8.0 - 1.0
