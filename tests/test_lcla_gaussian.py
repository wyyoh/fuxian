"""离散高斯 reference sampler 测试。"""

from __future__ import annotations

import numpy as np

from lattice_aka_repro.lcla_gaussian import (
    DiscreteGaussianSampler,
    gaussian_tail_cutoff,
    sample_discrete_gaussian,
)


def test_same_seed_reproducible_and_shape_correct() -> None:
    first = sample_discrete_gaussian(shape=(6, 32), beta=3.192, seed=73)
    second = sample_discrete_gaussian(shape=(6, 32), beta=3.192, seed=73)
    different = sample_discrete_gaussian(shape=(6, 32), beta=3.192, seed=74)
    assert first.centered.shape == (6, 32)
    assert np.array_equal(first.centered, second.centered)
    assert not np.array_equal(first.centered, different.centered)
    assert np.max(np.abs(first.centered)) <= first.tail_cutoff
    assert first.sampler_family.startswith("discrete_gaussian_")


def test_empirical_symmetry_and_nonzero_support() -> None:
    sample = DiscreteGaussianSampler(beta=3.192, seed=91).sample((50_000,)).centered
    assert abs(float(np.mean(sample))) < 0.04
    assert np.any(sample < 0)
    assert np.any(sample > 0)
    for magnitude in (1, 2, 3):
        positive = int(np.count_nonzero(sample == magnitude))
        negative = int(np.count_nonzero(sample == -magnitude))
        assert abs(positive - negative) / max(positive + negative, 1) < 0.08


def test_tail_cutoff_is_explicit_and_effective() -> None:
    cutoff = gaussian_tail_cutoff(3.192)
    sample = sample_discrete_gaussian(shape=(20_000,), beta=3.192, seed=92)
    assert cutoff == sample.tail_cutoff
    assert np.max(np.abs(sample.centered)) <= cutoff
