"""C2LAKE Table 7/Figure 4 计时基准。

该脚本一次只测一个 profile，便于上层脚本按参数点启动独立子进程。
"""

from __future__ import annotations

# ruff: noqa: E402,I001

import argparse
import csv
import os

for _thread_var in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ.setdefault(_thread_var, "1")

import platform
import subprocess
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, TypeVar

import numpy as np

from lattice_aka_repro.c2lake_core import (
    C2LakeCoreError,
    C2LakeKeyPair,
    C2LakeMasterSecret,
    C2LakeProfile,
    C2LakePublicParameters,
    extract_partial_private_key,
    load_c2lake_profile,
    set_secret_value,
    setup,
    verify_and_assemble_key,
)
from lattice_aka_repro.c2lake_protocol import (
    C2LakeSessionResult,
    C2LakeTimestampPolicy,
    initiator_create_request,
    initiator_verify_and_finish,
    make_protocol_context,
    responder_verify_and_reply,
    run_handshake,
)

_PHASES: Final = (
    "Setup",
    "SetSecretValue",
    "PartialPrivateKeyExtract",
    "initiator_create",
    "responder_verify_and_reply",
    "initiator_verify_and_finish",
    "responder_total",
    "initiator_total",
    "full_handshake",
)
_T = TypeVar("_T")


@dataclass(frozen=True, slots=True)
class BenchmarkRow:
    protocol: str
    profile: str
    family: str
    m: int
    q: int
    n: int
    phase: str
    repetition: int
    seed: int
    backend: str
    elapsed_ns: int
    success: bool
    error_code: str
    git_commit: str
    python_version: str
    numpy_version: str
    cpu: str
    os: str
    timestamp_utc: str
    matrix_numpy_bytes: int
    estimated_peak_bytes: int
    available_memory_bytes: int | None
    measurement_kind: str
    actual_execution_attempted: bool
    timeout_scope: str
    parent_attempt_id: str


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--profile", required=True)
    parser.add_argument("--backend", default="fast", choices=("safe", "fast"))
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--repetitions", type=int, default=100)
    parser.add_argument("--seed-base", type=int, default=900_000)
    parser.add_argument(
        "--raw-output",
        type=Path,
        default=Path("artifacts/raw/C2LAKE/benchmark_raw.csv"),
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--mode", choices=("smoke", "exact"), default="exact")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    rows = run_profile_benchmark(
        repo_root=args.repo_root,
        profile_name=args.profile,
        backend=args.backend,
        warmup=args.warmup,
        repetitions=args.repetitions,
        seed_base=args.seed_base,
        mode=args.mode,
    )
    append_rows(args.raw_output, rows, resume=args.resume)
    print(args.raw_output)
    return 0 if all(row.success for row in rows) else 1


def run_profile_benchmark(
    *,
    repo_root: Path,
    profile_name: str,
    backend: str,
    warmup: int,
    repetitions: int,
    seed_base: int,
    mode: str,
) -> list[BenchmarkRow]:
    profile = load_c2lake_profile(profile_name, specs_dir=repo_root / "specs")
    environment = _environment(repo_root)
    matrix_bytes = profile.n * profile.n * 8
    peak_bytes = _estimated_peak_bytes(profile.n)
    available_memory = _available_memory_bytes()
    if available_memory is not None and peak_bytes > int(available_memory * 0.85):
        return _failure_rows(
            profile_name=profile_name,
            family=profile.family,
            m=profile.m,
            q=profile.q,
            n=profile.n,
            backend=backend,
            repetitions=repetitions,
            seed_base=seed_base,
            environment=environment,
            matrix_bytes=matrix_bytes,
            peak_bytes=peak_bytes,
            available_memory=available_memory,
            error_code="resource_limited",
        )

    for warmup_index in range(warmup):
        _run_iteration(profile_name, backend, seed_base + 10_000_000 + warmup_index, warmup_index)

    rows: list[BenchmarkRow] = []
    for repetition in range(repetitions):
        rows.extend(
            _rows_for_iteration(
                repo_root=repo_root,
                profile_name=profile_name,
                backend=backend,
                seed=seed_base + repetition * 1_000,
                repetition=repetition,
                environment=environment,
                matrix_bytes=matrix_bytes,
                peak_bytes=peak_bytes,
                available_memory=available_memory,
                mode=mode,
            )
        )
    return rows


def append_rows(output: Path, rows: list[BenchmarkRow], *, resume: bool) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    existing_keys: set[tuple[str, str, int, str]] = set()
    if output.exists():
        if not resume:
            raise FileExistsError(f"{output} 已存在；使用 --resume 追加缺失项")
        with output.open(newline="", encoding="utf-8") as handle:
            for reader_row in csv.DictReader(handle):
                existing_keys.add(
                    (
                        reader_row["profile"],
                        reader_row["phase"],
                        int(reader_row["repetition"]),
                        reader_row["backend"],
                    )
                )
    write_header = not output.exists()
    with output.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()))
        if write_header:
            writer.writeheader()
        for row in rows:
            key = (row.profile, row.phase, row.repetition, row.backend)
            if key in existing_keys:
                continue
            writer.writerow(asdict(row))
    return output


def phase_names() -> tuple[str, ...]:
    return _PHASES


def _rows_for_iteration(
    *,
    repo_root: Path,
    profile_name: str,
    backend: str,
    seed: int,
    repetition: int,
    environment: dict[str, str],
    matrix_bytes: int,
    peak_bytes: int,
    available_memory: int | None,
    mode: str,
) -> list[BenchmarkRow]:
    profile = load_c2lake_profile(profile_name, specs_dir=repo_root / "specs")
    timestamp = _timestamp_utc()
    rows: list[BenchmarkRow] = []
    try:
        setup_elapsed, setup_result = _measure(
            lambda: setup(profile_name, seed=seed, backend=backend)
        )
        public_params, master_secret = setup_result
        rows.append(
            _row(
                profile,
                "Setup",
                repetition,
                seed,
                backend,
                setup_elapsed,
                True,
                "",
                environment,
                timestamp,
                matrix_bytes,
                peak_bytes,
                available_memory,
            )
        )
        set_elapsed, alice_user = _measure(
            lambda: set_secret_value(public_params, "alice@example.test", seed=seed + 1)
        )
        rows.append(
            _row(
                profile,
                "SetSecretValue",
                repetition,
                seed + 1,
                backend,
                set_elapsed,
                True,
                "",
                environment,
                timestamp,
                matrix_bytes,
                peak_bytes,
                available_memory,
            )
        )
        partial_elapsed, alice_partial = _measure(
            lambda: extract_partial_private_key(
                public_params,
                master_secret,
                "alice@example.test",
                alice_user.p_i1,
                seed=seed + 2,
            )
        )
        rows.append(
            _row(
                profile,
                "PartialPrivateKeyExtract",
                repetition,
                seed + 2,
                backend,
                partial_elapsed,
                True,
                "",
                environment,
                timestamp,
                matrix_bytes,
                peak_bytes,
                available_memory,
            )
        )
        alice_key_pair = verify_and_assemble_key(
            public_params,
            "alice@example.test",
            alice_user,
            alice_partial,
        )
        bob_key_pair = _make_key_pair(
            public_params,
            master_secret,
            "bob@example.test",
            secret_seed=seed + 3,
            partial_seed=seed + 4,
        )
        policy = C2LakeTimestampPolicy(max_clock_skew=10, max_message_age=60)
        alice_context = make_protocol_context(public_params, alice_key_pair, "alice@example.test")
        bob_context = make_protocol_context(public_params, bob_key_pair, "bob@example.test")
        initiator_elapsed, request_state = _measure(
            lambda: initiator_create_request(
                alice_context,
                bob_context.identity,
                timestamp=1_000,
                seed=seed + 5,
            )
        )
        request, initiator_state = request_state
        rows.append(
            _row(
                profile,
                "initiator_create",
                repetition,
                seed + 5,
                backend,
                initiator_elapsed,
                True,
                "",
                environment,
                timestamp,
                matrix_bytes,
                peak_bytes,
                available_memory,
            )
        )
        responder_elapsed, responder_state = _measure(
            lambda: responder_verify_and_reply(
                bob_context,
                request,
                timestamp=1_001,
                seed=seed + 6,
                now=1_001,
                timestamp_policy=policy,
            )
        )
        response, _bob_ephemeral, _bob_result = responder_state
        rows.append(
            _row(
                profile,
                "responder_verify_and_reply",
                repetition,
                seed + 6,
                backend,
                responder_elapsed,
                True,
                "",
                environment,
                timestamp,
                matrix_bytes,
                peak_bytes,
                available_memory,
            )
        )
        finish_elapsed, _alice_result = _measure(
            lambda: initiator_verify_and_finish(
                alice_context,
                request,
                initiator_state,
                response,
                now=1_001,
                timestamp_policy=policy,
            )
        )
        rows.append(
            _row(
                profile,
                "initiator_verify_and_finish",
                repetition,
                seed + 7,
                backend,
                finish_elapsed,
                True,
                "",
                environment,
                timestamp,
                matrix_bytes,
                peak_bytes,
                available_memory,
            )
        )
        rows.append(
            _row(
                profile,
                "responder_total",
                repetition,
                seed + 6,
                backend,
                responder_elapsed,
                True,
                "",
                environment,
                timestamp,
                matrix_bytes,
                peak_bytes,
                available_memory,
            )
        )
        rows.append(
            _row(
                profile,
                "initiator_total",
                repetition,
                seed + 5,
                backend,
                initiator_elapsed + finish_elapsed,
                True,
                "",
                environment,
                timestamp,
                matrix_bytes,
                peak_bytes,
                available_memory,
            )
        )
        full_elapsed, full_results = _measure(
            lambda: run_handshake(
                public_params,
                alice_key_pair,
                bob_key_pair,
                "alice@example.test",
                "bob@example.test",
                seed + 8,
                seed + 9,
                1_000,
                1_001,
                1_001,
                policy,
            )
        )
        _assert_successful_session(full_results)
        rows.append(
            _row(
                profile,
                "full_handshake",
                repetition,
                seed + 8,
                backend,
                full_elapsed,
                True,
                "",
                environment,
                timestamp,
                matrix_bytes,
                peak_bytes,
                available_memory,
            )
        )
    except Exception as error:
        rows.extend(
            _failure_rows(
                profile_name=profile_name,
                family=profile.family,
                m=profile.m,
                q=profile.q,
                n=profile.n,
                backend=backend,
                repetitions=1,
                seed_base=seed,
                environment=environment,
                matrix_bytes=matrix_bytes,
                peak_bytes=peak_bytes,
                available_memory=available_memory,
                error_code=_error_code(error),
                repetition_start=repetition,
            )
        )
    if mode == "smoke":
        _assert_rows_have_required_phases(rows)
    return rows


def _run_iteration(
    profile_name: str,
    backend: str,
    seed: int,
    repetition: int,
) -> None:
    _rows_for_iteration(
        repo_root=Path.cwd(),
        profile_name=profile_name,
        backend=backend,
        seed=seed,
        repetition=repetition,
        environment=_environment(Path.cwd()),
        matrix_bytes=0,
        peak_bytes=0,
        available_memory=_available_memory_bytes(),
        mode="exact",
    )


def _measure(callable_: Callable[[], _T]) -> tuple[int, _T]:
    started = time.perf_counter_ns()
    result = callable_()
    elapsed = time.perf_counter_ns() - started
    return elapsed, result


def _make_key_pair(
    public_params: C2LakePublicParameters,
    master_secret: C2LakeMasterSecret,
    identity: str,
    *,
    secret_seed: int,
    partial_seed: int,
) -> C2LakeKeyPair:
    user_secret = set_secret_value(public_params, identity, seed=secret_seed)
    partial_key = extract_partial_private_key(
        public_params,
        master_secret,
        identity,
        user_secret.p_i1,
        seed=partial_seed,
    )
    return verify_and_assemble_key(public_params, identity, user_secret, partial_key)


def _assert_successful_session(
    results: tuple[C2LakeSessionResult, C2LakeSessionResult],
) -> None:
    initiator_result, responder_result = results
    if not initiator_result.accepted or not responder_result.accepted:
        raise C2LakeCoreError("BENCHMARK_PROTOCOL_FAILURE", "握手未 accepted")
    if initiator_result.components != responder_result.components:
        raise C2LakeCoreError("BENCHMARK_PROTOCOL_FAILURE", "K1/K2/K3 不一致")
    if initiator_result.session_key_scalar != responder_result.session_key_scalar:
        raise C2LakeCoreError("BENCHMARK_PROTOCOL_FAILURE", "session scalar 不一致")


def _assert_rows_have_required_phases(rows: list[BenchmarkRow]) -> None:
    phases = {row.phase for row in rows}
    missing = set(_PHASES).difference(phases)
    if missing:
        raise C2LakeCoreError("BENCHMARK_PIPELINE_FAILURE", f"缺少阶段：{sorted(missing)}")


def _failure_rows(
    *,
    profile_name: str,
    family: str,
    m: int,
    q: int,
    n: int,
    backend: str,
    repetitions: int,
    seed_base: int,
    environment: dict[str, str],
    matrix_bytes: int,
    peak_bytes: int,
    available_memory: int | None,
    error_code: str,
    repetition_start: int = 0,
) -> list[BenchmarkRow]:
    timestamp = _timestamp_utc()
    measurement_kind, actual_execution_attempted, timeout_scope, parent_attempt_id = (
        _failure_measurement_metadata(error_code, profile_name, timestamp)
    )
    rows: list[BenchmarkRow] = []
    for repetition in range(repetition_start, repetition_start + repetitions):
        for phase in _PHASES:
            rows.append(
                BenchmarkRow(
                    protocol="C2LAKE",
                    profile=profile_name,
                    family=family,
                    m=m,
                    q=q,
                    n=n,
                    phase=phase,
                    repetition=repetition,
                    seed=seed_base + repetition * 1_000,
                    backend=backend,
                    elapsed_ns=0,
                    success=False,
                    error_code=error_code,
                    git_commit=environment["git_commit"],
                    python_version=environment["python_version"],
                    numpy_version=environment["numpy_version"],
                    cpu=environment["cpu"],
                    os=environment["os"],
                    timestamp_utc=timestamp,
                    matrix_numpy_bytes=matrix_bytes,
                    estimated_peak_bytes=peak_bytes,
                    available_memory_bytes=available_memory,
                    measurement_kind=measurement_kind,
                    actual_execution_attempted=actual_execution_attempted,
                    timeout_scope=timeout_scope,
                    parent_attempt_id=parent_attempt_id,
                )
            )
    return rows


def _row(
    profile: C2LakeProfile,
    phase: str,
    repetition: int,
    seed: int,
    backend: str,
    elapsed_ns: int,
    success: bool,
    error_code: str,
    environment: dict[str, str],
    timestamp_utc: str,
    matrix_bytes: int,
    peak_bytes: int,
    available_memory: int | None,
) -> BenchmarkRow:
    return BenchmarkRow(
        protocol="C2LAKE",
        profile=profile.name,
        family=profile.family,
        m=profile.m,
        q=profile.q,
        n=profile.n,
        phase=phase,
        repetition=repetition,
        seed=seed,
        backend=backend,
        elapsed_ns=elapsed_ns,
        success=success,
        error_code=error_code,
        git_commit=environment["git_commit"],
        python_version=environment["python_version"],
        numpy_version=environment["numpy_version"],
        cpu=environment["cpu"],
        os=environment["os"],
        timestamp_utc=timestamp_utc,
        matrix_numpy_bytes=matrix_bytes,
        estimated_peak_bytes=peak_bytes,
        available_memory_bytes=available_memory,
        measurement_kind="measured_success" if success else "measured_failure",
        actual_execution_attempted=True,
        timeout_scope="",
        parent_attempt_id="",
    )


def _failure_measurement_metadata(
    error_code: str,
    profile_name: str,
    timestamp_utc: str,
) -> tuple[str, bool, str, str]:
    if error_code == "resource_limited":
        return (
            "resource_limit_placeholder",
            False,
            "profile_resource_precheck",
            f"{profile_name}:resource_limit:{timestamp_utc}",
        )
    return ("measured_failure", True, "", "")


def _error_code(error: Exception) -> str:
    if isinstance(error, C2LakeCoreError):
        return error.code
    return type(error).__name__


def _estimated_peak_bytes(n: int) -> int:
    matrix_bytes = n * n * 8
    vector_workspace = 80 * n * 8
    return matrix_bytes * 2 + vector_workspace


def _available_memory_bytes() -> int | None:
    meminfo = Path("/proc/meminfo")
    if not meminfo.is_file():
        return None
    for line in meminfo.read_text(encoding="utf-8").splitlines():
        if line.startswith("MemAvailable:"):
            parts = line.split()
            if len(parts) >= 2:
                return int(parts[1]) * 1024
    return None


def _environment(repo_root: Path) -> dict[str, str]:
    return {
        "git_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            text=True,
        ).strip(),
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "cpu": _cpu_description(),
        "os": platform.platform(),
    }


def _cpu_description() -> str:
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        for line in cpuinfo.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.lower().startswith("model name"):
                return line.split(":", 1)[1].strip()
    return platform.processor() or "unknown"


def _timestamp_utc() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
