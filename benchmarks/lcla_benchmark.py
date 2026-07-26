"""LCLA-AKA Table IV 原语与 constructed 协议阶段基准。"""

from __future__ import annotations

# ruff: noqa: E402,I001

import os

for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ.setdefault(_thread_variable, "1")

import csv
import platform
import subprocess
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import Final, TypeVar

import numpy as np

from lattice_aka_repro.lcla_backends import (
    generate_static_key_pair,
    load_lcla_profile,
    setup_lcla,
)
from lattice_aka_repro.lcla_gaussian import DiscreteGaussianSampler
from lattice_aka_repro.lcla_hashes import LCLAHashSuite, xor_identity
from lattice_aka_repro.lcla_modular import (
    matrix_add_mod,
    matrix_vector_mod,
    transpose_matrix_matrix_mod,
    transpose_matrix_vector_mod,
    vector_add_mod,
)
from lattice_aka_repro.lcla_protocol import (
    alice_create_request,
    alice_finish,
    bob_finish,
    bob_respond,
    make_lcla_context,
    run_lcla_handshake,
    validate_session_pair,
)
from lattice_aka_repro.lcla_reconciliation import mod2, signal
from lattice_aka_repro.lcla_types import DistributionVariant, LCLAError, LCLAProfile

TABLE_IV_OPERATIONS: Final = (
    "T_mul0",
    "T_mul1",
    "T_mul2",
    "T_add0",
    "T_add1",
    "T_Samp0",
    "T_Samp1",
    "T_Samp2",
    "T_xor",
    "T_H2",
    "T_H1",
    "T_mod0",
    "T_mod1",
    "T_Sign",
    "T_Mod",
)
PROTOCOL_PHASES: Final = (
    "initiator_create",
    "responder_verify_and_reply",
    "initiator_verify_and_finish",
    "responder_finish",
)
_T = TypeVar("_T")


@dataclass(frozen=True, slots=True)
class LCLABenchmarkRow:
    protocol: str
    profile: str
    backend: str
    keygen_backend: str
    operation: str
    phase: str
    repetition: int
    seed: int
    elapsed_ns: int
    success: bool
    error_code: str
    measurement_kind: str
    actual_execution_attempted: bool
    timeout_scope: str
    parent_attempt_id: str
    git_commit: str
    python_version: str
    numpy_version: str
    compiler: str
    cpu: str
    os: str
    timestamp_utc: str
    distribution_variant: str = "legacy_reference"
    sampling_condition: str = "not_applicable"
    attempt_accepted: bool | None = None
    rejection_stage: str = ""
    retry_index: int = 0
    conditional_on_success: bool = False
    retry_time_included: bool = False


def run_table_iv_benchmark(
    *,
    repo_root: Path,
    profile_name: str,
    warmup: int,
    repetitions: int,
    seed_base: int,
    distribution_variant: DistributionVariant = "legacy_reference",
    operations: tuple[str, ...] = TABLE_IV_OPERATIONS,
) -> list[LCLABenchmarkRow]:
    """测量 Table IV 的 NumPy reference 映射。"""

    if warmup < 0 or repetitions <= 0:
        raise ValueError("warmup 必须非负且 repetitions 必须为正")
    profile = load_lcla_profile(repo_root, profile_name)
    environment = _environment(repo_root)
    for index in range(warmup):
        callbacks = _operation_callbacks(
            profile,
            seed_base + 10_000_000 + index,
            distribution_variant=distribution_variant,
        )
        for operation in operations:
            callbacks[operation]()
    rows: list[LCLABenchmarkRow] = []
    for repetition in range(repetitions):
        seed = seed_base + repetition
        callbacks = _operation_callbacks(
            profile,
            seed,
            distribution_variant=distribution_variant,
        )
        for operation in operations:
            rows.append(
                _measure_row(
                    profile=profile,
                    backend="numpy_reference",
                    keygen_backend="not_applicable",
                    operation=operation,
                    phase="table_iv_operation",
                    repetition=repetition,
                    seed=seed,
                    callback=callbacks[operation],
                    environment=environment,
                    distribution_variant=distribution_variant,
                )
            )
    parent = f"{profile.name}-external-capabilities"
    rows.extend(
        (
            _placeholder_row(
                profile=profile,
                backend="frodo_native",
                keygen_backend="not_applicable",
                operation="frodo_native_lcla_operations",
                phase="dependency_probe",
                error_code="UNSUPPORTED_PARAMETER_AND_MISSING_LCLA_API",
                parent_attempt_id=parent,
                environment=environment,
                distribution_variant=distribution_variant,
            ),
            _placeholder_row(
                profile=profile,
                backend="unavailable",
                keygen_backend="real_trapdoor",
                operation="TrapGen",
                phase="static_key_generation",
                error_code="DEPENDENCY_UNAVAILABLE",
                parent_attempt_id=parent,
                environment=environment,
                distribution_variant=distribution_variant,
            ),
            _placeholder_row(
                profile=profile,
                backend="unavailable",
                keygen_backend="real_trapdoor",
                operation="SamplePre",
                phase="static_key_generation",
                error_code="DEPENDENCY_UNAVAILABLE",
                parent_attempt_id=parent,
                environment=environment,
                distribution_variant=distribution_variant,
            ),
        )
    )
    return rows


def run_constructed_static_benchmark(
    *,
    repo_root: Path,
    profile_name: str,
    warmup: int,
    repetitions: int,
    seed_base: int,
    distribution_variant: DistributionVariant = "legacy_reference",
) -> list[LCLABenchmarkRow]:
    """测量 reference setup + constructed static-key 流程。"""

    profile = load_lcla_profile(repo_root, profile_name)
    environment = _environment(repo_root)
    for index in range(warmup):
        _constructed_static_once(
            profile,
            seed_base + 10_000_000 + index,
            distribution_variant,
        )
    return [
        _measure_row(
            profile=profile,
            backend="numpy_reference",
            keygen_backend="constructed_relation",
            operation="constructed_static_keygen",
            phase="static_key_generation",
            repetition=repetition,
            seed=seed_base + repetition,
            callback=partial(
                _constructed_static_once,
                profile,
                seed_base + repetition,
                distribution_variant,
            ),
            environment=environment,
            distribution_variant=distribution_variant,
        )
        for repetition in range(repetitions)
    ]


def run_protocol_phase_benchmark(
    *,
    repo_root: Path,
    profile_name: str,
    repetitions: int,
    seed_base: int,
    search_limit_per_repetition: int = 2_000,
    distribution_variant: DistributionVariant = "legacy_reference",
) -> list[LCLABenchmarkRow]:
    """测量条件成功路径；seed 搜索和失败耗时明确不计入。"""

    profile = load_lcla_profile(repo_root, profile_name)
    parameters = setup_lcla(
        profile=profile,
        backend="fast",
        keygen_backend="constructed_relation",
        seed=seed_base + 1,
        distribution_variant=distribution_variant,
    )
    alice = generate_static_key_pair(parameters, "Alice", seed=seed_base + 2)
    bob = generate_static_key_pair(parameters, "Bob", seed=seed_base + 3)
    context = make_lcla_context(parameters)
    environment = _environment(repo_root)
    rows: list[LCLABenchmarkRow] = []
    candidate = seed_base + 100
    for repetition in range(repetitions):
        accepted: tuple[int, int] | None = None
        accepted_retry_index = 0
        last_error = "NO_ACCEPTED_SEED_WITHIN_SEARCH_WINDOW"
        for attempt_index in range(search_limit_per_repetition):
            initiator_seed = candidate
            responder_seed = candidate + 100_000
            candidate += 1
            try:
                run_lcla_handshake(
                    context,
                    alice,
                    bob,
                    "Alice",
                    "Bob",
                    initiator_seed=initiator_seed,
                    responder_seed=responder_seed,
                )
            except LCLAError as exc:
                last_error = exc.code
                continue
            accepted = initiator_seed, responder_seed
            accepted_retry_index = attempt_index
            break
        if accepted is None:
            for phase in PROTOCOL_PHASES:
                rows.append(
                    _failure_row(
                        profile=profile,
                        operation="constructed_protocol",
                        phase=phase,
                        repetition=repetition,
                        seed=candidate,
                        error_code=last_error,
                        environment=environment,
                        distribution_variant=distribution_variant,
                        sampling_condition="accepted_seed_search",
                        retry_index=search_limit_per_repetition,
                    )
                )
            continue
        initiator_seed, responder_seed = accepted
        elapsed, request_and_state = _measure(
            partial(
                alice_create_request,
                context,
                alice,
                "Alice",
                "Bob",
                seed=initiator_seed,
            )
        )
        request, alice_state = request_and_state
        rows.append(
            _success_row(
                profile,
                "constructed_protocol",
                "initiator_create",
                repetition,
                initiator_seed,
                elapsed,
                environment,
                distribution_variant=distribution_variant,
                sampling_condition="accepted_seed_search",
                retry_index=accepted_retry_index,
                conditional_on_success=True,
            )
        )
        elapsed, response_and_state = _measure(
            partial(
                bob_respond,
                context,
                bob,
                "Bob",
                request,
                seed=responder_seed,
            )
        )
        response, bob_state = response_and_state
        rows.append(
            _success_row(
                profile,
                "constructed_protocol",
                "responder_verify_and_reply",
                repetition,
                responder_seed,
                elapsed,
                environment,
                distribution_variant=distribution_variant,
                sampling_condition="accepted_seed_search",
                retry_index=accepted_retry_index,
                conditional_on_success=True,
            )
        )
        elapsed, finish_state_result = _measure(
            partial(
                alice_finish,
                context,
                alice,
                "Alice",
                "Bob",
                request,
                alice_state,
                response,
                seed=initiator_seed + 2_000_003,
            )
        )
        finish, _alice_final_state, alice_result = finish_state_result
        rows.append(
            _success_row(
                profile,
                "constructed_protocol",
                "initiator_verify_and_finish",
                repetition,
                initiator_seed + 2_000_003,
                elapsed,
                environment,
                distribution_variant=distribution_variant,
                sampling_condition="accepted_seed_search",
                retry_index=accepted_retry_index,
                conditional_on_success=True,
            )
        )
        elapsed, bob_result = _measure(
            partial(
                bob_finish,
                context,
                bob,
                "Bob",
                request,
                response,
                bob_state,
                finish,
            )
        )
        validate_session_pair(alice_result, bob_result)
        rows.append(
            _success_row(
                profile,
                "constructed_protocol",
                "responder_finish",
                repetition,
                responder_seed,
                elapsed,
                environment,
                distribution_variant=distribution_variant,
                sampling_condition="accepted_seed_search",
                retry_index=accepted_retry_index,
                conditional_on_success=True,
            )
        )
    return rows


def run_unconditioned_attempt_benchmark(
    *,
    repo_root: Path,
    profile_name: str,
    repetitions: int,
    seed_base: int,
    distribution_variant: DistributionVariant,
) -> list[LCLABenchmarkRow]:
    """测量连续 seed 的全部完整尝试，成功和拒绝均保留。"""

    profile = load_lcla_profile(repo_root, profile_name)
    parameters = setup_lcla(
        profile=profile,
        backend="fast",
        keygen_backend="constructed_relation",
        seed=seed_base,
        distribution_variant=distribution_variant,
    )
    alice = generate_static_key_pair(parameters, "Alice", seed=seed_base + 1)
    bob = generate_static_key_pair(parameters, "Bob", seed=seed_base + 2)
    context = make_lcla_context(parameters)
    environment = _environment(repo_root)
    rows: list[LCLABenchmarkRow] = []
    for repetition in range(repetitions):
        initiator_seed = seed_base + 10_000 + repetition
        responder_seed = seed_base + 100_000 + repetition
        started = time.perf_counter_ns()
        try:
            run_lcla_handshake(
                context,
                alice,
                bob,
                "Alice",
                "Bob",
                initiator_seed=initiator_seed,
                responder_seed=responder_seed,
            )
        except Exception as exc:
            elapsed = time.perf_counter_ns() - started
            code = exc.code if isinstance(exc, LCLAError) else type(exc).__name__
            rows.append(
                _row(
                    profile,
                    "numpy_reference",
                    "constructed_relation",
                    "unconditioned_attempt_latency",
                    "full_handshake",
                    repetition,
                    initiator_seed,
                    elapsed,
                    False,
                    code,
                    "measured_failure",
                    True,
                    "",
                    f"{profile.name}-{distribution_variant}-unconditioned-{repetition}",
                    environment,
                    distribution_variant=distribution_variant,
                    sampling_condition="continuous_seed_no_replacement",
                    attempt_accepted=False,
                    rejection_stage=code,
                    retry_index=0,
                    conditional_on_success=False,
                    retry_time_included=False,
                )
            )
        else:
            rows.append(
                _row(
                    profile,
                    "numpy_reference",
                    "constructed_relation",
                    "unconditioned_attempt_latency",
                    "full_handshake",
                    repetition,
                    initiator_seed,
                    time.perf_counter_ns() - started,
                    True,
                    "",
                    "measured_success",
                    True,
                    "",
                    f"{profile.name}-{distribution_variant}-unconditioned-{repetition}",
                    environment,
                    distribution_variant=distribution_variant,
                    sampling_condition="continuous_seed_no_replacement",
                    attempt_accepted=True,
                    rejection_stage="",
                    retry_index=0,
                    conditional_on_success=False,
                    retry_time_included=False,
                )
            )
    return rows


def run_retry_until_success_benchmark(
    *,
    repo_root: Path,
    profile_name: str,
    repetitions: int,
    seed_base: int,
    distribution_variant: DistributionVariant,
    max_attempts_per_repetition: int = 1_000,
) -> list[LCLABenchmarkRow]:
    """测量显式重试路径，逐次耗时和端到端总耗时均写入 raw。"""

    profile = load_lcla_profile(repo_root, profile_name)
    parameters = setup_lcla(
        profile=profile,
        backend="fast",
        keygen_backend="constructed_relation",
        seed=seed_base,
        distribution_variant=distribution_variant,
    )
    alice = generate_static_key_pair(parameters, "Alice", seed=seed_base + 1)
    bob = generate_static_key_pair(parameters, "Bob", seed=seed_base + 2)
    context = make_lcla_context(parameters)
    environment = _environment(repo_root)
    rows: list[LCLABenchmarkRow] = []
    candidate = seed_base + 10_000
    for repetition in range(repetitions):
        parent = f"{profile.name}-{distribution_variant}-retry-{repetition}"
        total_started = time.perf_counter_ns()
        accepted = False
        last_error = "RETRY_LIMIT_REACHED"
        for retry_index in range(max_attempts_per_repetition):
            initiator_seed = candidate
            responder_seed = candidate + 100_000
            candidate += 1
            attempt_started = time.perf_counter_ns()
            try:
                run_lcla_handshake(
                    context,
                    alice,
                    bob,
                    "Alice",
                    "Bob",
                    initiator_seed=initiator_seed,
                    responder_seed=responder_seed,
                )
            except Exception as exc:
                elapsed = time.perf_counter_ns() - attempt_started
                last_error = exc.code if isinstance(exc, LCLAError) else type(exc).__name__
                rows.append(
                    _row(
                        profile,
                        "numpy_reference",
                        "constructed_relation",
                        "retry_until_success_latency",
                        "attempt",
                        repetition,
                        initiator_seed,
                        elapsed,
                        False,
                        last_error,
                        "measured_failure",
                        True,
                        "",
                        parent,
                        environment,
                        distribution_variant=distribution_variant,
                        sampling_condition="retry_until_success",
                        attempt_accepted=False,
                        rejection_stage=last_error,
                        retry_index=retry_index,
                        conditional_on_success=False,
                        retry_time_included=True,
                    )
                )
                continue
            elapsed = time.perf_counter_ns() - attempt_started
            accepted = True
            rows.append(
                _row(
                    profile,
                    "numpy_reference",
                    "constructed_relation",
                    "retry_until_success_latency",
                    "attempt",
                    repetition,
                    initiator_seed,
                    elapsed,
                    True,
                    "",
                    "measured_success",
                    True,
                    "",
                    parent,
                    environment,
                    distribution_variant=distribution_variant,
                    sampling_condition="retry_until_success",
                    attempt_accepted=True,
                    rejection_stage="",
                    retry_index=retry_index,
                    conditional_on_success=False,
                    retry_time_included=True,
                )
            )
            break
        total_elapsed = time.perf_counter_ns() - total_started
        rows.append(
            _row(
                profile,
                "numpy_reference",
                "constructed_relation",
                "retry_until_success_latency",
                "total_end_to_end",
                repetition,
                candidate - 1,
                total_elapsed,
                accepted,
                "" if accepted else last_error,
                "measured_success" if accepted else "measured_failure",
                True,
                "",
                parent,
                environment,
                distribution_variant=distribution_variant,
                sampling_condition="retry_until_success",
                attempt_accepted=accepted,
                rejection_stage="" if accepted else last_error,
                retry_index=sum(1 for row in rows if row.parent_attempt_id == parent) - 1,
                conditional_on_success=False,
                retry_time_included=True,
            )
        )
    return rows


def append_rows(output: Path, rows: list[LCLABenchmarkRow], *, resume: bool) -> None:
    """不可覆盖地写 raw CSV；resume 只追加缺失 key。"""

    if not rows:
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and not resume:
        raise FileExistsError(f"{output} 已存在；必须使用 --resume")
    existing: set[tuple[str, str, str, str, str, int, int, str]] = set()
    if output.exists():
        with output.open(encoding="utf-8", newline="") as handle:
            for reader_row in csv.DictReader(handle):
                existing.add(
                    (
                        reader_row["profile"],
                        reader_row["backend"],
                        reader_row["operation"],
                        reader_row["phase"],
                        reader_row.get("distribution_variant", "legacy_reference"),
                        int(reader_row["repetition"]),
                        int(reader_row.get("retry_index", "0")),
                        reader_row.get("sampling_condition", "not_applicable"),
                    )
                )
    write_header = not output.exists()
    with output.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(asdict(rows[0]).keys()),
            lineterminator="\n",
        )
        if write_header:
            writer.writeheader()
        for row in rows:
            key = (
                row.profile,
                row.backend,
                row.operation,
                row.phase,
                row.distribution_variant,
                row.repetition,
                row.retry_index,
                row.sampling_condition,
            )
            if key not in existing:
                writer.writerow(asdict(row))


def _operation_callbacks(
    profile: LCLAProfile,
    seed: int,
    *,
    distribution_variant: DistributionVariant = "legacy_reference",
) -> dict[str, Callable[[], object]]:
    rng = np.random.Generator(np.random.PCG64(seed))
    q = profile.q
    m = profile.m
    n = profile.n
    matrix_a = rng.integers(0, q, size=(n, m), dtype=np.int64)
    matrix_x = rng.integers(0, q, size=(n, m), dtype=np.int64)
    matrix_mm = rng.integers(0, q, size=(m, m), dtype=np.int64)
    matrix_mm_2 = rng.integers(0, q, size=(m, m), dtype=np.int64)
    vector_m = rng.integers(0, q, size=m, dtype=np.int64)
    vector_m_2 = rng.integers(0, q, size=m, dtype=np.int64)
    vector_n = rng.integers(0, q, size=n, dtype=np.int64)
    bits = rng.integers(0, 2, size=m, dtype=np.int64)
    hash_suite = LCLAHashSuite(profile=profile, programmed=False)
    identity = b"A" * max(1, (m + 7) // 8)
    return {
        "T_mul0": lambda: transpose_matrix_matrix_mod(matrix_x, matrix_a, q=q, backend="fast"),
        "T_mul1": lambda: matrix_vector_mod(matrix_mm, vector_m, q=q, backend="fast"),
        "T_mul2": lambda: transpose_matrix_vector_mod(matrix_x, vector_n, q=q, backend="fast"),
        "T_add0": lambda: matrix_add_mod(matrix_mm, matrix_mm_2, q=q),
        "T_add1": lambda: vector_add_mod(vector_m, vector_m_2, q=q),
        "T_Samp0": lambda: np.random.Generator(np.random.PCG64(seed + 17)).integers(
            0, q, size=(m, n), dtype=np.int64
        ),
        "T_Samp1": lambda: DiscreteGaussianSampler(
            beta=profile.beta,
            seed=seed + 18,
            exponent_variant=(
                "paper_definition3"
                if distribution_variant == "paper_literal_distribution"
                else "standard_lattice"
            ),
        ).sample((m, m)),
        "T_Samp2": lambda: DiscreteGaussianSampler(
            beta=profile.beta,
            seed=seed + 19,
            exponent_variant=(
                "paper_definition3"
                if distribution_variant == "paper_literal_distribution"
                else "standard_lattice"
            ),
        ).sample((m,)),
        "T_xor": lambda: xor_identity(identity, bytes([0xA5]) * len(identity)),
        "T_H2": lambda: hash_suite.mac_a(matrix_mm, bits, bits),
        "T_H1": lambda: hash_suite.h1(identity),
        "T_mod0": lambda: np.remainder(matrix_mm + q, q),
        "T_mod1": lambda: np.remainder(vector_m + q, q),
        "T_Sign": lambda: signal(vector_m, q=q, seed=seed + 20),
        "T_Mod": lambda: mod2(vector_m, bits, q=q),
    }


def _constructed_static_once(
    profile: LCLAProfile,
    seed: int,
    distribution_variant: DistributionVariant = "legacy_reference",
) -> object:
    parameters = setup_lcla(
        profile=profile,
        backend="fast",
        keygen_backend="constructed_relation",
        seed=seed,
        distribution_variant=distribution_variant,
    )
    return generate_static_key_pair(parameters, f"Entity-{seed}", seed=seed + 1)


def _measure(callback: Callable[[], _T]) -> tuple[int, _T]:
    started = time.perf_counter_ns()
    result = callback()
    return time.perf_counter_ns() - started, result


def _measure_row(
    *,
    profile: LCLAProfile,
    backend: str,
    keygen_backend: str,
    operation: str,
    phase: str,
    repetition: int,
    seed: int,
    callback: Callable[[], object],
    environment: dict[str, str],
    distribution_variant: DistributionVariant = "legacy_reference",
) -> LCLABenchmarkRow:
    try:
        elapsed, _ = _measure(callback)
    except Exception as exc:  # benchmark 必须保留真实失败
        code = exc.code if isinstance(exc, LCLAError) else type(exc).__name__
        return _row(
            profile,
            backend,
            keygen_backend,
            operation,
            phase,
            repetition,
            seed,
            0,
            False,
            code,
            "measured_failure",
            True,
            "",
            f"{profile.name}-{operation}-{repetition}",
            environment,
            distribution_variant=distribution_variant,
            sampling_condition="unconditioned_operation",
        )
    return _row(
        profile,
        backend,
        keygen_backend,
        operation,
        phase,
        repetition,
        seed,
        elapsed,
        True,
        "",
        "measured_success",
        True,
        "",
        f"{profile.name}-{operation}-{repetition}",
        environment,
        distribution_variant=distribution_variant,
        sampling_condition="unconditioned_operation",
    )


def _success_row(
    profile: LCLAProfile,
    operation: str,
    phase: str,
    repetition: int,
    seed: int,
    elapsed: int,
    environment: dict[str, str],
    *,
    distribution_variant: DistributionVariant = "legacy_reference",
    sampling_condition: str = "not_applicable",
    retry_index: int = 0,
    conditional_on_success: bool = False,
) -> LCLABenchmarkRow:
    return _row(
        profile,
        "numpy_reference",
        "constructed_relation",
        "conditional_success_path_latency" if operation == "constructed_protocol" else operation,
        phase,
        repetition,
        seed,
        elapsed,
        True,
        "",
        "measured_success",
        True,
        "",
        f"{profile.name}-protocol-{repetition}",
        environment,
        distribution_variant=distribution_variant,
        sampling_condition=sampling_condition,
        attempt_accepted=True,
        retry_index=retry_index,
        conditional_on_success=conditional_on_success,
        retry_time_included=False,
    )


def _failure_row(
    *,
    profile: LCLAProfile,
    operation: str,
    phase: str,
    repetition: int,
    seed: int,
    error_code: str,
    environment: dict[str, str],
    distribution_variant: DistributionVariant = "legacy_reference",
    sampling_condition: str = "not_applicable",
    retry_index: int = 0,
) -> LCLABenchmarkRow:
    return _row(
        profile,
        "numpy_reference",
        "constructed_relation",
        operation,
        phase,
        repetition,
        seed,
        0,
        False,
        error_code,
        "measured_failure",
        True,
        "seed_search",
        f"{profile.name}-protocol-{repetition}",
        environment,
        distribution_variant=distribution_variant,
        sampling_condition=sampling_condition,
        attempt_accepted=False,
        rejection_stage=error_code,
        retry_index=retry_index,
        conditional_on_success=sampling_condition == "accepted_seed_search",
        retry_time_included=False,
    )


def _placeholder_row(
    *,
    profile: LCLAProfile,
    backend: str,
    keygen_backend: str,
    operation: str,
    phase: str,
    error_code: str,
    parent_attempt_id: str,
    environment: dict[str, str],
    distribution_variant: DistributionVariant = "legacy_reference",
) -> LCLABenchmarkRow:
    return _row(
        profile,
        backend,
        keygen_backend,
        operation,
        phase,
        -1,
        0,
        0,
        False,
        error_code,
        "dependency_unavailable_placeholder",
        False,
        "dependency_probe",
        parent_attempt_id,
        environment,
        distribution_variant=distribution_variant,
        sampling_condition="dependency_unavailable",
    )


def _row(
    profile: LCLAProfile,
    backend: str,
    keygen_backend: str,
    operation: str,
    phase: str,
    repetition: int,
    seed: int,
    elapsed_ns: int,
    success: bool,
    error_code: str,
    measurement_kind: str,
    actual_execution_attempted: bool,
    timeout_scope: str,
    parent_attempt_id: str,
    environment: dict[str, str],
    *,
    distribution_variant: str = "legacy_reference",
    sampling_condition: str = "not_applicable",
    attempt_accepted: bool | None = None,
    rejection_stage: str = "",
    retry_index: int = 0,
    conditional_on_success: bool = False,
    retry_time_included: bool = False,
) -> LCLABenchmarkRow:
    return LCLABenchmarkRow(
        protocol="LCLA-AKA",
        profile=profile.name,
        backend=backend,
        keygen_backend=keygen_backend,
        operation=operation,
        phase=phase,
        repetition=repetition,
        seed=seed,
        elapsed_ns=elapsed_ns,
        success=success,
        error_code=error_code,
        measurement_kind=measurement_kind,
        actual_execution_attempted=actual_execution_attempted,
        timeout_scope=timeout_scope,
        parent_attempt_id=parent_attempt_id,
        git_commit=environment["git_commit"],
        python_version=platform.python_version(),
        numpy_version=np.__version__,
        compiler=platform.python_compiler(),
        cpu=platform.processor() or platform.machine(),
        os=platform.platform(),
        timestamp_utc=datetime.now(UTC).isoformat(),
        distribution_variant=distribution_variant,
        sampling_condition=sampling_condition,
        attempt_accepted=attempt_accepted,
        rejection_stage=rejection_stage,
        retry_index=retry_index,
        conditional_on_success=conditional_on_success,
        retry_time_included=retry_time_included,
    )


def _environment(repo_root: Path) -> dict[str, str]:
    return {
        "git_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            text=True,
        ).strip()
    }
