from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
import numpy.typing as npt
import pytest
import yaml

from lattice_aka_repro.c2lake_core import (
    C2LakeCoreError,
    C2LakePartialPrivateKey,
    C2LakePublicParameters,
    C2LakeUserSecret,
    bounded_ternary_vector,
    centered_norm,
    dot_mod,
    encode_zq_array,
    extract_partial_private_key,
    matrix_times_vector,
    set_secret_value,
    setup,
    vector_times_matrix,
    verify_and_assemble_key,
    verify_partial_key,
)
from lattice_aka_repro.randomness import seeded_rng

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SPECS_DIR = _REPO_ROOT / "specs"
_SEEDS = range(100)


@pytest.mark.parametrize("profile", ["toy", "paper_literal_m32", "audited_prime_m32"])
def test_partial_key_validation_passes_for_100_seeds(profile: str) -> None:
    for seed in _SEEDS:
        public_params, master_secret = setup(profile, seed=seed, backend="safe")
        user_secret = set_secret_value(public_params, "alice@example.test", seed=1_000 + seed)
        partial_key = extract_partial_private_key(
            public_params,
            master_secret,
            "alice@example.test",
            user_secret.p_i1,
            seed=2_000 + seed,
        )

        assert verify_partial_key(
            public_params,
            "alice@example.test",
            user_secret,
            partial_key,
        )
        key_pair = verify_and_assemble_key(
            public_params,
            "alice@example.test",
            user_secret,
            partial_key,
        )
        assert key_pair.public_key.shape == (public_params.n,)
        assert key_pair.private_key.shape == (public_params.n,)


@pytest.mark.parametrize("identity", ["", b"", None, 42, object()])
def test_empty_and_invalid_identity_returns_stable_error(identity: object) -> None:
    public_params, _ = setup("toy", seed=70, backend="safe")

    with pytest.raises(C2LakeCoreError) as error_info:
        set_secret_value(public_params, identity, seed=71)
    assert error_info.value.code == "IDENTITY_ERROR"


def test_unicode_and_bytes_identity_are_normalized() -> None:
    public_params, master_secret = setup("toy", seed=72, backend="safe")
    unicode_identity = "用户@example.test/🚀"
    user_secret = set_secret_value(public_params, unicode_identity, seed=73)
    partial_key = extract_partial_private_key(
        public_params,
        master_secret,
        unicode_identity,
        user_secret.p_i1,
        seed=74,
    )
    assert user_secret.identity == unicode_identity.encode("utf-8")
    assert verify_partial_key(public_params, unicode_identity, user_secret, partial_key)

    identity_bytes = b"alice@example.test"
    bytes_user = set_secret_value(public_params, identity_bytes, seed=75)
    assert bytes_user.identity == identity_bytes
    assert bytes_user.identity is not identity_bytes


def test_bounded_ternary_vectors_have_centered_norm_within_beta() -> None:
    public_params, master_secret = setup("audited_prime_m32", seed=7, backend="safe")
    assert centered_norm(master_secret.vector, q=public_params.q) <= public_params.beta

    user_secret = set_secret_value(public_params, b"alice", seed=8)
    assert centered_norm(user_secret.d_i1, q=public_params.q) <= public_params.beta

    for seed in range(200):
        vector = bounded_ternary_vector(
            seeded_rng(seed),
            public_params.n,
            q=public_params.q,
            beta=public_params.beta,
        )
        assert np.any(vector)
        assert centered_norm(vector, q=public_params.q) <= public_params.beta


def test_same_seed_outputs_are_identical_and_readonly() -> None:
    first_params, first_master = setup("toy", seed=9, backend="safe")
    second_params, second_master = setup("toy", seed=9, backend="safe")
    assert np.array_equal(first_params.matrix, second_params.matrix)
    assert np.array_equal(first_params.public_key, second_params.public_key)
    assert np.array_equal(first_master.vector, second_master.vector)
    assert not first_params.matrix.flags.writeable
    assert not first_params.public_key.flags.writeable
    assert not first_master.vector.flags.writeable

    first_user = set_secret_value(first_params, "alice", seed=10)
    second_user = set_secret_value(first_params, "alice", seed=10)
    assert np.array_equal(first_user.d_i1, second_user.d_i1)
    assert np.array_equal(first_user.p_i1, second_user.p_i1)


def test_different_seed_outputs_are_not_all_identical() -> None:
    first_params, first_master = setup("toy", seed=11, backend="safe")
    second_params, second_master = setup("toy", seed=12, backend="safe")

    assert not (
        np.array_equal(first_params.matrix, second_params.matrix)
        and np.array_equal(first_params.public_key, second_params.public_key)
        and np.array_equal(first_master.vector, second_master.vector)
    )


def test_safe_and_fast_backends_match_for_toy() -> None:
    safe_params, safe_master = setup("toy", seed=13, backend="safe")
    fast_params, fast_master = setup("toy", seed=13, backend="fast")
    assert np.array_equal(safe_params.matrix, fast_params.matrix)
    assert np.array_equal(safe_params.public_key, fast_params.public_key)
    assert np.array_equal(safe_master.vector, fast_master.vector)

    user_seed = 14
    extraction_seed = 15
    safe_user = set_secret_value(safe_params, "alice", seed=user_seed)
    fast_user = set_secret_value(fast_params, "alice", seed=user_seed)
    assert np.array_equal(safe_user.d_i1, fast_user.d_i1)
    assert np.array_equal(safe_user.p_i1, fast_user.p_i1)

    safe_partial = extract_partial_private_key(
        safe_params,
        safe_master,
        "alice",
        safe_user.p_i1,
        seed=extraction_seed,
    )
    fast_partial = extract_partial_private_key(
        fast_params,
        fast_master,
        "alice",
        fast_user.p_i1,
        seed=extraction_seed,
    )
    assert np.array_equal(safe_partial.d_i0, fast_partial.d_i0)
    assert np.array_equal(safe_partial.p_i0, fast_partial.p_i0)

    assert np.array_equal(
        vector_times_matrix(
            safe_master.vector,
            safe_params.matrix,
            q=safe_params.q,
            backend="safe",
        ),
        vector_times_matrix(
            fast_master.vector,
            fast_params.matrix,
            q=fast_params.q,
            backend="fast",
        ),
    )
    assert np.array_equal(
        matrix_times_vector(
            safe_params.matrix,
            safe_master.vector,
            q=safe_params.q,
            backend="safe",
        ),
        matrix_times_vector(
            fast_params.matrix,
            fast_master.vector,
            q=fast_params.q,
            backend="fast",
        ),
    )


def test_matrix_orientation_known_answer_for_safe_and_fast_backends() -> None:
    q = 17
    matrix = np.array(
        [
            [1, 2, 3],
            [4, 5, 6],
            [7, 8, 9],
        ],
        dtype=np.int64,
    )
    vector = np.array([2, 3, 5], dtype=np.int64)
    expected_vector_times_matrix = np.array([15, 8, 1], dtype=np.int64)
    expected_matrix_times_vector = np.array([6, 2, 15], dtype=np.int64)

    assert not np.array_equal(expected_vector_times_matrix, expected_matrix_times_vector)
    for backend in ("safe", "fast"):
        assert np.array_equal(
            vector_times_matrix(vector, matrix, q=q, backend=backend),
            expected_vector_times_matrix,
        )
        assert np.array_equal(
            matrix_times_vector(matrix, vector, q=q, backend=backend),
            expected_matrix_times_vector,
        )


@pytest.mark.parametrize("tamper", ["identity", "d_i0", "p_i0", "p_i1", "P"])
def test_tampering_partial_key_inputs_fails(tamper: str) -> None:
    public_params, master_secret = setup("toy", seed=20, backend="safe")
    identity = "alice"
    user_secret = set_secret_value(public_params, identity, seed=21)
    partial_key = extract_partial_private_key(
        public_params,
        master_secret,
        identity,
        user_secret.p_i1,
        seed=22,
    )

    checked_identity = identity
    checked_params = public_params
    checked_user = user_secret
    checked_partial = partial_key
    if tamper == "identity":
        checked_identity = "mallory"
    elif tamper == "d_i0":
        checked_partial = C2LakePartialPrivateKey(
            identity=partial_key.identity,
            q=partial_key.q,
            profile=partial_key.profile,
            backend=partial_key.backend,
            d_i0=_tamper_vector(partial_key.d_i0, partial_key.q),
            p_i0=partial_key.p_i0,
        )
    elif tamper == "p_i0":
        checked_partial = C2LakePartialPrivateKey(
            identity=partial_key.identity,
            q=partial_key.q,
            profile=partial_key.profile,
            backend=partial_key.backend,
            d_i0=partial_key.d_i0,
            p_i0=_tamper_vector(partial_key.p_i0, partial_key.q),
        )
    elif tamper == "p_i1":
        checked_user = C2LakeUserSecret(
            identity=user_secret.identity,
            q=user_secret.q,
            profile=user_secret.profile,
            backend=user_secret.backend,
            d_i1=user_secret.d_i1,
            p_i1=_tamper_vector(user_secret.p_i1, user_secret.q),
        )
    else:
        checked_params = C2LakePublicParameters(
            n=public_params.n,
            q=public_params.q,
            beta=public_params.beta,
            profile=public_params.profile,
            family=public_params.family,
            backend=public_params.backend,
            secret_sampling=public_params.secret_sampling,
            matrix=public_params.matrix,
            public_key=_tamper_vector(public_params.public_key, public_params.q),
            hash_suite=public_params.hash_suite,
        )

    assert not verify_partial_key(
        checked_params,
        checked_identity,
        checked_user,
        checked_partial,
    )
    with pytest.raises(C2LakeCoreError) as error_info:
        verify_and_assemble_key(
            checked_params,
            checked_identity,
            checked_user,
            checked_partial,
        )
    assert error_info.value.code == "INVALID_PARTIAL_KEY"


def test_stable_error_codes_for_shape_domain_profile_and_backend(tmp_path: Path) -> None:
    public_params, _ = setup("toy", seed=30, backend="safe")
    user_secret = set_secret_value(public_params, "alice", seed=31)
    wrong_q_user = C2LakeUserSecret(
        identity=user_secret.identity,
        q=263,
        profile=user_secret.profile,
        backend=user_secret.backend,
        d_i1=user_secret.d_i1,
        p_i1=user_secret.p_i1,
    )

    with pytest.raises(C2LakeCoreError) as shape_error:
        vector_times_matrix(
            np.array([1, 2], dtype=np.int64),
            public_params.matrix,
            q=public_params.q,
        )
    assert shape_error.value.code == "SHAPE_ERROR"

    with pytest.raises(C2LakeCoreError) as domain_error:
        vector_times_matrix(
            np.full(public_params.n, public_params.q, dtype=np.int64),
            public_params.matrix,
            q=public_params.q,
        )
    assert domain_error.value.code == "DOMAIN_ERROR"

    with pytest.raises(C2LakeCoreError) as profile_error:
        setup("not_a_profile", seed=30)
    assert profile_error.value.code == "PROFILE_ERROR"

    with pytest.raises(C2LakeCoreError) as backend_error:
        setup("toy", seed=30, backend="unsafe")
    assert backend_error.value.code == "BACKEND_ERROR"

    with pytest.raises(C2LakeCoreError) as q_error:
        verify_partial_key(
            public_params,
            "alice",
            wrong_q_user,
            C2LakePartialPrivateKey(
                identity=b"alice",
                q=public_params.q,
                profile=public_params.profile,
                backend=public_params.backend,
                d_i0=np.zeros(public_params.n, dtype=np.int64),
                p_i0=np.zeros(public_params.n, dtype=np.int64),
            ),
        )
    assert q_error.value.code == "MODULUS_ERROR"

    specs_dir = _copy_specs(tmp_path)
    profile_path = specs_dir / "c2lake" / "parameter_profiles.yaml"
    document = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    document["profiles"]["audited_prime_m32"]["q"] = 1024
    profile_path.write_text(
        yaml.safe_dump(document, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    with pytest.raises(C2LakeCoreError) as audited_error:
        setup("audited_prime_m32", seed=30, specs_dir=specs_dir)
    assert audited_error.value.code == "PROFILE_ERROR"


def test_paper_literal_composite_q_is_accepted() -> None:
    public_params, master_secret = setup("paper_literal_m32", seed=40, backend="safe")
    assert public_params.q == 1024
    assert master_secret.q == 1024


def test_fast_backend_rejects_unsafe_int64_accumulator() -> None:
    q = 5_000_000_000
    vector = np.array([q - 1, q - 1, q - 1], dtype=np.int64)
    matrix = np.full((3, 3), q - 1, dtype=np.int64)

    with pytest.raises(C2LakeCoreError) as error_info:
        vector_times_matrix(vector, matrix, q=q, backend="fast")
    assert error_info.value.code == "BACKEND_OVERFLOW_UNSAFE"


def test_safe_backend_uses_python_int_fallback_when_int64_accumulator_is_unsafe() -> None:
    q = 5_000_000_000
    vector = np.array([q - 1, q - 2, q - 3], dtype=np.int64)
    other = np.array([q - 10, q - 11, q - 12], dtype=np.int64)
    matrix = np.array(
        [
            [q - 1, q - 2, q - 3],
            [q - 4, q - 5, q - 6],
            [q - 7, q - 8, q - 9],
        ],
        dtype=np.int64,
    )

    expected_vector_times_matrix = np.array(
        [
            sum(int(vector[row]) * int(matrix[row, column]) for row in range(3)) % q
            for column in range(3)
        ],
        dtype=np.int64,
    )
    expected_matrix_times_vector = np.array(
        [
            sum(int(matrix[row, column]) * int(other[column]) for column in range(3)) % q
            for row in range(3)
        ],
        dtype=np.int64,
    )
    expected_dot = (
        sum(int(left) * int(right) for left, right in zip(vector, other, strict=True)) % q
    )

    for operation in (
        lambda: vector_times_matrix(vector, matrix, q=q, backend="fast"),
        lambda: matrix_times_vector(matrix, other, q=q, backend="fast"),
        lambda: dot_mod(vector, other, q=q, backend="fast"),
    ):
        with pytest.raises(C2LakeCoreError) as error_info:
            operation()
        assert error_info.value.code == "BACKEND_OVERFLOW_UNSAFE"

    assert np.array_equal(
        vector_times_matrix(vector, matrix, q=q, backend="safe"),
        expected_vector_times_matrix,
    )
    assert np.array_equal(
        matrix_times_vector(matrix, other, q=q, backend="safe"),
        expected_matrix_times_vector,
    )
    assert dot_mod(vector, other, q=q, backend="safe") == expected_dot


def test_hash_encoding_is_deterministic_and_sensitive_to_inputs() -> None:
    public_params, master_secret = setup("toy", seed=50, backend="safe")
    user_secret = set_secret_value(public_params, "alice", seed=51)
    partial_key = extract_partial_private_key(
        public_params,
        master_secret,
        "alice",
        user_secret.p_i1,
        seed=52,
    )

    hash_suite = public_params.hash_suite
    encoded = hash_suite.encode_h1(
        "alice",
        partial_key.p_i0,
        user_secret.p_i1,
        public_params.public_key,
        q=public_params.q,
    )
    assert encoded == hash_suite.encode_h1(
        "alice",
        partial_key.p_i0,
        user_secret.p_i1,
        public_params.public_key,
        q=public_params.q,
    )
    assert encoded != hash_suite.encode_h1(
        "bob",
        partial_key.p_i0,
        user_secret.p_i1,
        public_params.public_key,
        q=public_params.q,
    )
    assert encoded != hash_suite.encode_h1(
        "alice",
        _tamper_vector(partial_key.p_i0, public_params.q),
        user_secret.p_i1,
        public_params.public_key,
        q=public_params.q,
    )
    assert encoded != hash_suite.encode_h1(
        "alice",
        partial_key.p_i0,
        user_secret.p_i1,
        public_params.public_key,
        q=public_params.q + 1,
    )
    assert encode_zq_array(public_params.public_key, q=public_params.q) != encode_zq_array(
        public_params.public_key.reshape(1, -1),
        q=public_params.q,
    )

    h1_first = hash_suite.h1(
        "alice",
        partial_key.p_i0,
        user_secret.p_i1,
        public_params.public_key,
        q=public_params.q,
    )
    h1_second = hash_suite.h1(
        "alice",
        partial_key.p_i0,
        user_secret.p_i1,
        public_params.public_key,
        q=public_params.q,
    )
    assert h1_first == h1_second
    assert 1 <= h1_first <= public_params.q - 1


def test_h2_h3_type_safe_interfaces_return_zq_star() -> None:
    public_params, _ = setup("toy", seed=60, backend="safe")
    zero = np.zeros(public_params.n, dtype=np.int64)
    h2_value = public_params.hash_suite.h2(
        "alice",
        zero,
        zero,
        public_params.public_key,
        zero,
        zero,
        123456,
        q=public_params.q,
    )
    h3_value = public_params.hash_suite.h3(
        zero,
        zero,
        public_params.public_key,
        zero,
        zero,
        zero,
        zero,
        zero,
        public_params.public_key,
        zero,
        1,
        2,
        3,
        q=public_params.q,
    )

    assert 1 <= h2_value <= public_params.q - 1
    assert 1 <= h3_value <= public_params.q - 1


def _tamper_vector(vector: npt.NDArray[np.int64], q: int) -> npt.NDArray[np.int64]:
    tampered = vector.copy()
    tampered[0] = (int(tampered[0]) + 1) % q
    return tampered


def _copy_specs(tmp_path: Path) -> Path:
    destination = tmp_path / "specs"
    shutil.copytree(_SPECS_DIR, destination)
    return destination
