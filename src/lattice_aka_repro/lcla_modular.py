"""LCLA-AKA 的模 q 线性代数后端。"""

from __future__ import annotations

from typing import Literal, cast

import numpy as np
import numpy.typing as npt

from lattice_aka_repro.lcla_types import IntArray, LCLAError

Backend = Literal["safe", "fast"]
_INT64_MAX = np.iinfo(np.int64).max


def _integer_array(value: npt.ArrayLike, *, ndim: int, name: str) -> IntArray:
    raw = np.asarray(value)
    if raw.ndim != ndim:
        raise LCLAError("SHAPE_ERROR", f"{name} 必须是 {ndim} 维数组")
    if not np.issubdtype(raw.dtype, np.integer):
        raise LCLAError("DTYPE_ERROR", f"{name} 必须使用整数 dtype")
    try:
        return np.asarray(raw, dtype=np.int64)
    except (OverflowError, ValueError) as exc:
        raise LCLAError("DTYPE_ERROR", f"{name} 元素不能表示为 int64") from exc


def _validate_q_backend(q: int, backend: str) -> Backend:
    if isinstance(q, bool) or not isinstance(q, int) or q <= 2:
        raise LCLAError("MODULUS_ERROR", "q 必须为大于 2 的整数")
    if backend not in {"safe", "fast"}:
        raise LCLAError("BACKEND_ERROR", f"不支持 backend={backend!r}")
    return cast(Backend, backend)


def _accumulation_safe(inner: int, left: IntArray, right: IntArray) -> bool:
    if inner == 0:
        return True
    left_abs = max(abs(int(left.min(initial=0))), abs(int(left.max(initial=0))))
    right_abs = max(abs(int(right.min(initial=0))), abs(int(right.max(initial=0))))
    return inner * left_abs * right_abs <= _INT64_MAX


def matrix_matrix_mod(
    left: npt.ArrayLike,
    right: npt.ArrayLike,
    *,
    q: int,
    backend: str = "safe",
) -> IntArray:
    """计算 left @ right mod q；safe 必要时回退 Python int。"""

    selected = _validate_q_backend(q, backend)
    left_array = _integer_array(left, ndim=2, name="left")
    right_array = _integer_array(right, ndim=2, name="right")
    if left_array.shape[1] != right_array.shape[0]:
        raise LCLAError("SHAPE_ERROR", "矩阵乘法内维不一致")
    rows, inner = left_array.shape
    columns = right_array.shape[1]
    if _accumulation_safe(inner, left_array, right_array):
        return np.asarray((left_array @ right_array) % q, dtype=np.int64)
    if selected == "fast":
        raise LCLAError("BACKEND_OVERFLOW_UNSAFE", "int64 最坏累加范围不安全")
    result = np.empty((rows, columns), dtype=np.int64)
    for row in range(rows):
        for column in range(columns):
            total = 0
            for index in range(inner):
                total += int(left_array[row, index]) * int(right_array[index, column])
            result[row, column] = total % q
    return result


def matrix_vector_mod(
    matrix: npt.ArrayLike,
    vector: npt.ArrayLike,
    *,
    q: int,
    backend: str = "safe",
) -> IntArray:
    """计算 matrix @ vector mod q。"""

    selected = _validate_q_backend(q, backend)
    matrix_array = _integer_array(matrix, ndim=2, name="matrix")
    vector_array = _integer_array(vector, ndim=1, name="vector")
    if matrix_array.shape[1] != vector_array.shape[0]:
        raise LCLAError("SHAPE_ERROR", "matrix/vector 内维不一致")
    rows, inner = matrix_array.shape
    if _accumulation_safe(inner, matrix_array, vector_array):
        return np.asarray((matrix_array @ vector_array) % q, dtype=np.int64)
    if selected == "fast":
        raise LCLAError("BACKEND_OVERFLOW_UNSAFE", "int64 最坏累加范围不安全")
    result = np.empty(rows, dtype=np.int64)
    for row in range(rows):
        total = 0
        for index in range(inner):
            total += int(matrix_array[row, index]) * int(vector_array[index])
        result[row] = total % q
    return result


def transpose_matrix_matrix_mod(
    left: npt.ArrayLike,
    right: npt.ArrayLike,
    *,
    q: int,
    backend: str = "safe",
) -> IntArray:
    """计算 left.T @ right mod q。"""

    left_array = _integer_array(left, ndim=2, name="left")
    right_array = _integer_array(right, ndim=2, name="right")
    if left_array.shape[0] != right_array.shape[0]:
        raise LCLAError("SHAPE_ERROR", "left.T/right 内维不一致")
    return matrix_matrix_mod(left_array.T, right_array, q=q, backend=backend)


def transpose_matrix_vector_mod(
    matrix: npt.ArrayLike,
    vector: npt.ArrayLike,
    *,
    q: int,
    backend: str = "safe",
) -> IntArray:
    """计算 matrix.T @ vector mod q。"""

    matrix_array = _integer_array(matrix, ndim=2, name="matrix")
    vector_array = _integer_array(vector, ndim=1, name="vector")
    if matrix_array.shape[0] != vector_array.shape[0]:
        raise LCLAError("SHAPE_ERROR", "matrix.T/vector 内维不一致")
    return matrix_vector_mod(matrix_array.T, vector_array, q=q, backend=backend)


def vector_add_mod(left: npt.ArrayLike, right: npt.ArrayLike, *, q: int) -> IntArray:
    """逐元素加法并立即 mod q。"""

    _validate_q_backend(q, "safe")
    left_array = _integer_array(left, ndim=1, name="left")
    right_array = _integer_array(right, ndim=1, name="right")
    if left_array.shape != right_array.shape:
        raise LCLAError("SHAPE_ERROR", "向量 shape 不一致")
    return np.asarray(
        [(int(a) + int(b)) % q for a, b in zip(left_array, right_array, strict=True)],
        dtype=np.int64,
    )


def vector_sub_mod(left: npt.ArrayLike, right: npt.ArrayLike, *, q: int) -> IntArray:
    """逐元素减法并立即 mod q。"""

    _validate_q_backend(q, "safe")
    left_array = _integer_array(left, ndim=1, name="left")
    right_array = _integer_array(right, ndim=1, name="right")
    if left_array.shape != right_array.shape:
        raise LCLAError("SHAPE_ERROR", "向量 shape 不一致")
    return np.asarray(
        [(int(a) - int(b)) % q for a, b in zip(left_array, right_array, strict=True)],
        dtype=np.int64,
    )


def scalar_multiply_mod(scalar: int, value: npt.ArrayLike, *, q: int) -> IntArray:
    """标量乘数组并立即 mod q，使用 Python int 避免溢出。"""

    _validate_q_backend(q, "safe")
    array = np.asarray(value)
    if not np.issubdtype(array.dtype, np.integer):
        raise LCLAError("DTYPE_ERROR", "value 必须使用整数 dtype")
    flat = np.asarray(
        [(int(scalar) * int(item)) % q for item in array.flat],
        dtype=np.int64,
    )
    return flat.reshape(array.shape)


def centered_representative(value: npt.ArrayLike, *, q: int) -> IntArray:
    """返回范围 [-floor(q/2), floor(q/2)] 的 centered representative。"""

    _validate_q_backend(q, "safe")
    array = np.asarray(value)
    if not np.issubdtype(array.dtype, np.integer):
        raise LCLAError("DTYPE_ERROR", "value 必须使用整数 dtype")
    half = q // 2
    flat = [((int(item) + half) % q) - half for item in array.flat]
    return np.asarray(flat, dtype=np.int64).reshape(array.shape)


def map_centered_to_zq(value: npt.ArrayLike, *, q: int) -> IntArray:
    """将 centered integer 映射到 Zq。"""

    _validate_q_backend(q, "safe")
    array = np.asarray(value)
    if not np.issubdtype(array.dtype, np.integer):
        raise LCLAError("DTYPE_ERROR", "centered value 必须使用整数 dtype")
    return np.asarray([int(item) % q for item in array.flat], dtype=np.int64).reshape(array.shape)


def pack_bits(bits: npt.ArrayLike) -> bytes:
    """按 little-bit-order 打包 bit vector。"""

    array = _integer_array(bits, ndim=1, name="bits")
    if np.any((array != 0) & (array != 1)):
        raise LCLAError("DOMAIN_ERROR", "bits 必须属于 {0,1}")
    return np.packbits(array.astype(np.uint8), bitorder="little").tobytes()


def unpack_bits(data: bytes, *, bit_length: int) -> IntArray:
    """解包固定长度 bit vector。"""

    if bit_length <= 0:
        raise LCLAError("ENCODING_ERROR", "bit_length 必须为正")
    available = len(data) * 8
    if available < bit_length:
        raise LCLAError("ENCODING_ERROR", "字节串不足以解出指定位数")
    bits = np.unpackbits(np.frombuffer(bytes(data), dtype=np.uint8), bitorder="little")
    return np.asarray(bits[:bit_length], dtype=np.int64)
