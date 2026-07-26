"""LCLA identity、编码和域分离测试。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from lattice_aka_repro.lcla_backends import load_lcla_profile
from lattice_aka_repro.lcla_hashes import (
    LCLAHashSuite,
    encode_zq_array,
    normalize_identity,
    xor_identity,
)
from lattice_aka_repro.lcla_types import LCLAError

ROOT = Path(__file__).resolve().parents[1]


def test_identity_normalization_and_unicode_roundtrip() -> None:
    assert normalize_identity("服务器甲") == "服务器甲".encode()
    value = b"binary-identity"
    normalized = normalize_identity(value)
    assert normalized == value
    assert normalized is not value
    for invalid in ("", b"", None, 1):
        with pytest.raises(LCLAError, match="IDENTITY_ERROR"):
            normalize_identity(invalid)  # type: ignore[arg-type]


def test_encoding_changes_with_shape_q_profile_and_element() -> None:
    first = encode_zq_array(
        np.asarray([[1, 2]], dtype=np.int64),
        q=127,
        profile_version="toy",
        tag="array",
    )
    changed_shape = encode_zq_array(
        np.asarray([[1], [2]], dtype=np.int64),
        q=127,
        profile_version="toy",
        tag="array",
    )
    changed_q = encode_zq_array(
        np.asarray([[1, 2]], dtype=np.int64),
        q=131,
        profile_version="toy",
        tag="array",
    )
    changed_profile = encode_zq_array(
        np.asarray([[1, 2]], dtype=np.int64),
        q=127,
        profile_version="toy-v2",
        tag="array",
    )
    changed_element = encode_zq_array(
        np.asarray([[1, 3]], dtype=np.int64),
        q=127,
        profile_version="toy",
        tag="array",
    )
    assert len({first, changed_shape, changed_q, changed_profile, changed_element}) == 5


def test_h2_domains_output_exact_lengths_and_identity_mask() -> None:
    profile = load_lcla_profile(ROOT, "toy")
    suite = LCLAHashSuite(profile=profile, programmed=False)
    c = np.zeros((profile.m, profile.m), dtype=np.int64)
    bits = np.zeros(profile.m, dtype=np.int64)
    mac_a = suite.mac_a(c, bits, bits)
    mac_b = suite.mac_b(c, bits)
    assert mac_a.shape == (profile.m,)
    assert mac_b.shape == (profile.m,)
    assert not np.array_equal(mac_a, mac_b)
    identity = "匿名Alice".encode()
    mask = suite.identity_mask(bits, mac_a, c, bits, output_length=len(identity))
    assert len(mask) == len(identity)
    assert xor_identity(xor_identity(identity, mask), mask) == identity
    literal, audited = suite.session_key("匿名Alice", "Bob", bits, bits)
    assert len(literal) == profile.m // 8
    assert audited is None
