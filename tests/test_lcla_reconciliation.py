"""Definition 5 的端点、穷举和已识别 Lemma 3 边界测试。"""

from __future__ import annotations

import numpy as np
import pytest

from lattice_aka_repro.lcla_reconciliation import (
    lemma3_error_bound,
    mod2,
    mu_0,
    mu_1,
    signal,
)
from lattice_aka_repro.lcla_types import LCLAError


def test_mu_endpoints_from_paper() -> None:
    q = 127
    quarter = q // 4
    assert mu_0(-quarter, q=q) == 0
    assert mu_0(quarter, q=q) == 0
    assert mu_0(-quarter - 1, q=q) == 1
    assert mu_0(quarter + 1, q=q) == 1
    assert mu_1(-quarter + 1, q=q) == 0
    assert mu_1(quarter + 1, q=q) == 0
    assert mu_1(-quarter, q=q) == 1
    assert mu_1(quarter + 2, q=q) == 1


def test_toy_q_exhaustive_x_and_b() -> None:
    q = 127
    for value in range(q):
        for random_bit in (0, 1):
            expected = mu_0(value, q=q) if random_bit == 0 else mu_1(value, q=q)
            extracted = mod2(
                np.asarray([value], dtype=np.int64),
                np.asarray([expected], dtype=np.int64),
                q=q,
            )
            assert extracted.shape == (1,)
            assert int(extracted[0]) in (0, 1)


@pytest.mark.parametrize("q", [127, 16_777_215, 16_777_259])
def test_signal_reproducible_for_literal_and_audited_q(q: int) -> None:
    value = np.asarray([0, q // 4, q // 2, q - 1], dtype=np.int64)
    first = signal(value, q=q, seed=501)
    second = signal(value, q=q, seed=501)
    assert np.array_equal(first.delta, second.delta)
    assert np.array_equal(first.random_bits, second.random_bits)
    assert np.array_equal(mod2(value, first.delta, q=q), mod2(value, second.delta, q=q))


def test_lemma3_literal_formula_has_a_counterexample() -> None:
    """原文公式在模回绕处不满足其声称的充分条件，必须保留该事实。"""

    q = 127
    base = np.asarray([0], dtype=np.int64)
    error = -1
    close_value = np.asarray([(int(base[0]) + 2 * error) % q], dtype=np.int64)
    delta = np.asarray([mu_0(int(close_value[0]), q=q)], dtype=np.int64)
    assert abs(error) < lemma3_error_bound(q)
    assert not np.array_equal(
        mod2(close_value, delta, q=q),
        mod2(base, delta, q=q),
    )


def test_invalid_even_q_rejected() -> None:
    with pytest.raises(LCLAError, match="MODULUS_ERROR"):
        signal(np.asarray([1], dtype=np.int64), q=128, seed=1)
