"""LCLA 模运算的独立已知答案与溢出测试。"""

from __future__ import annotations

import numpy as np
import pytest

from lattice_aka_repro.lcla_modular import (
    matrix_matrix_mod,
    matrix_vector_mod,
    pack_bits,
    transpose_matrix_vector_mod,
    unpack_bits,
)
from lattice_aka_repro.lcla_types import LCLAError


@pytest.mark.parametrize("backend", ["safe", "fast"])
def test_asymmetric_known_answers(backend: str) -> None:
    matrix = np.asarray([[1, 2, 3], [4, 5, 6], [7, 8, 9]], dtype=np.int64)
    vector = np.asarray([2, 3, 5], dtype=np.int64)
    expected_matrix_vector = np.asarray([6, 2, 15], dtype=np.int64)
    expected_transpose_vector = np.asarray([15, 8, 1], dtype=np.int64)

    actual_matrix_vector = matrix_vector_mod(matrix, vector, q=17, backend=backend)
    actual_transpose_vector = transpose_matrix_vector_mod(matrix, vector, q=17, backend=backend)

    assert np.array_equal(actual_matrix_vector, expected_matrix_vector)
    assert np.array_equal(actual_transpose_vector, expected_transpose_vector)
    assert not np.array_equal(actual_matrix_vector, actual_transpose_vector)


def test_safe_python_int_fallback_and_fast_rejection() -> None:
    q = 4_000_000_007
    matrix = np.full((2, 2), q - 1, dtype=np.int64)
    vector = np.full(2, q - 1, dtype=np.int64)
    expected_vector = np.asarray([2, 2], dtype=np.int64)
    expected_matrix = np.full((2, 2), 2, dtype=np.int64)

    assert np.array_equal(matrix_vector_mod(matrix, vector, q=q, backend="safe"), expected_vector)
    assert np.array_equal(matrix_matrix_mod(matrix, matrix, q=q, backend="safe"), expected_matrix)
    with pytest.raises(LCLAError, match="BACKEND_OVERFLOW_UNSAFE"):
        matrix_vector_mod(matrix, vector, q=q, backend="fast")
    with pytest.raises(LCLAError, match="BACKEND_OVERFLOW_UNSAFE"):
        matrix_matrix_mod(matrix, matrix, q=q, backend="fast")


def test_bit_pack_roundtrip() -> None:
    bits = np.asarray([1, 0, 1, 1, 0, 0, 1, 0, 1], dtype=np.int64)
    assert np.array_equal(unpack_bits(pack_bits(bits), bit_length=len(bits)), bits)
