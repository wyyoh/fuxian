"""可审计、可复现的离散高斯参考采样器。"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np

from lattice_aka_repro.lcla_types import IntArray, LCLAError

GaussianExponentVariant = Literal["paper_definition3", "standard_lattice"]


@dataclass(frozen=True, slots=True)
class DiscreteGaussianSample:
    """一次采样及其审计元数据。"""

    centered: IntArray
    beta: float
    tail_cutoff: int
    sampler_family: str
    exponent_variant: GaussianExponentVariant
    seed: int

    def __post_init__(self) -> None:
        array = np.array(self.centered, dtype=np.int64, copy=True)
        array.setflags(write=False)
        object.__setattr__(self, "centered", array)


def gaussian_tail_cutoff(
    beta: float,
    *,
    tail_probability: float = 2.0**-64,
    exponent_variant: GaussianExponentVariant = "standard_lattice",
) -> int:
    """取显式有限支撑，使单点权重尾部受到保守限制。"""

    if not math.isfinite(beta) or beta <= 0:
        raise LCLAError("SAMPLER_ERROR", "beta 必须为有限正数")
    if not 0 < tail_probability < 1:
        raise LCLAError("SAMPLER_ERROR", "tail_probability 必须位于 (0,1)")
    if exponent_variant not in {"paper_definition3", "standard_lattice"}:
        raise LCLAError("SAMPLER_ERROR", f"未知 Gaussian exponent={exponent_variant!r}")
    denominator_factor = 2.0 if exponent_variant == "paper_definition3" else 1.0
    return max(
        1,
        math.ceil(
            beta * math.sqrt(denominator_factor * math.log(2.0 / tail_probability) / math.pi)
        ),
    )


class DiscreteGaussianSampler:
    """权重正比于 exp(-pi*k^2/beta^2) 的 PCG64 reference sampler。"""

    def __init__(
        self,
        *,
        beta: float,
        seed: int,
        tail_probability: float = 2.0**-64,
        exponent_variant: GaussianExponentVariant = "standard_lattice",
    ) -> None:
        if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
            raise LCLAError("SAMPLER_ERROR", "seed 必须为非负整数")
        self.beta = float(beta)
        self.seed = seed
        self.exponent_variant = exponent_variant
        self.tail_cutoff = gaussian_tail_cutoff(
            self.beta,
            tail_probability=tail_probability,
            exponent_variant=exponent_variant,
        )
        support = np.arange(-self.tail_cutoff, self.tail_cutoff + 1, dtype=np.int64)
        denominator_factor = 2.0 if exponent_variant == "paper_definition3" else 1.0
        weights = np.exp(
            -math.pi * np.square(support.astype(np.float64)) / (denominator_factor * self.beta**2)
        )
        self._support = support
        self._probabilities = weights / weights.sum()
        self._rng = np.random.Generator(np.random.PCG64(seed))

    def sample(self, shape: tuple[int, ...]) -> DiscreteGaussianSample:
        """采样 scalar/vector/matrix shape，返回 centered integer。"""

        if any(dimension <= 0 for dimension in shape):
            raise LCLAError("SHAPE_ERROR", "Gaussian sample shape 必须为正")
        centered = np.asarray(
            self._rng.choice(self._support, size=shape, p=self._probabilities),
            dtype=np.int64,
        )
        return DiscreteGaussianSample(
            centered=centered,
            beta=self.beta,
            tail_cutoff=self.tail_cutoff,
            sampler_family=(
                "discrete_gaussian_exp_minus_pi_k2_over_2beta2_pcg64"
                if self.exponent_variant == "paper_definition3"
                else "discrete_gaussian_exp_minus_pi_k2_over_beta2_pcg64"
            ),
            exponent_variant=self.exponent_variant,
            seed=self.seed,
        )

    def sample_scalar(self) -> int:
        """采样一个 centered integer。"""

        return int(self._rng.choice(self._support, p=self._probabilities))


def sample_discrete_gaussian(
    *,
    shape: tuple[int, ...],
    beta: float,
    seed: int,
    tail_probability: float = 2.0**-64,
    exponent_variant: GaussianExponentVariant = "standard_lattice",
) -> DiscreteGaussianSample:
    """便利接口：显式 seed 的一次采样。"""

    return DiscreteGaussianSampler(
        beta=beta,
        seed=seed,
        tail_probability=tail_probability,
        exponent_variant=exponent_variant,
    ).sample(shape)
