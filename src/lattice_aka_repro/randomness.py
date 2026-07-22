"""显式、可复现且不依赖 NumPy 全局状态的随机源。"""

from __future__ import annotations

import numpy as np

from lattice_aka_repro.errors import SeedNegativeError, SeedNotIntegerError


def validate_seed(seed: int) -> int:
    """验证 seed，并返回普通 Python 整数。"""

    if isinstance(seed, bool) or not isinstance(seed, int):
        raise SeedNotIntegerError("seed 必须是非布尔整数")
    if seed < 0:
        raise SeedNegativeError("seed 必须大于或等于 0")
    return seed


def seeded_rng(seed: int) -> np.random.Generator:
    """为给定 seed 创建固定使用 PCG64 的独立生成器。"""

    return np.random.Generator(np.random.PCG64(validate_seed(seed)))
