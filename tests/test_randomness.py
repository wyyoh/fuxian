from __future__ import annotations

import numpy as np
import pytest

from lattice_aka_repro.errors import SeedNegativeError, SeedNotIntegerError
from lattice_aka_repro.randomness import seeded_rng


def test_same_seed_produces_same_values() -> None:
    first = seeded_rng(20240722).integers(0, 2**31, size=32)
    second = seeded_rng(20240722).integers(0, 2**31, size=32)

    np.testing.assert_array_equal(first, second)


def test_rng_uses_explicit_pcg64() -> None:
    assert isinstance(seeded_rng(0).bit_generator, np.random.PCG64)


def test_negative_seed_has_stable_error_code() -> None:
    with pytest.raises(SeedNegativeError) as caught:
        seeded_rng(-1)

    assert caught.value.code == "SEED_NEGATIVE"


@pytest.mark.parametrize("seed", [True, 1.5, "1", None])
def test_non_integer_seed_has_stable_error_code(seed: object) -> None:
    with pytest.raises(SeedNotIntegerError) as caught:
        seeded_rng(seed)  # type: ignore[arg-type]

    assert caught.value.code == "SEED_NOT_INTEGER"
