"""LCLA-AKA 最终 validator 与 benchmark 语义回归测试。"""

from __future__ import annotations

from pathlib import Path

from benchmarks.lcla_benchmark import LCLABenchmarkRow, run_unconditioned_attempt_benchmark
from scripts.validate_lcla_full import validate_lcla_full

ROOT = Path(__file__).resolve().parents[1]


def test_distribution_variant_is_carried_by_benchmark() -> None:
    rows = run_unconditioned_attempt_benchmark(
        repo_root=ROOT,
        profile_name="toy",
        repetitions=1,
        seed_base=99_000_000,
        distribution_variant="paper_literal_distribution",
    )

    assert rows[0].distribution_variant == "paper_literal_distribution"


def test_conditional_unconditioned_and_retry_metadata_are_separate() -> None:
    conditional = _benchmark_row(
        operation="conditional_success_path_latency",
        sampling_condition="accepted_seed_search",
        conditional_on_success=True,
        retry_time_included=False,
    )
    unconditioned = _benchmark_row(
        operation="unconditioned_attempt_latency",
        sampling_condition="continuous_seed_no_replacement",
        conditional_on_success=False,
        retry_time_included=False,
    )
    retry = _benchmark_row(
        operation="retry_until_success_latency",
        sampling_condition="retry_until_success",
        retry_index=2,
        retry_time_included=True,
    )

    assert conditional.operation != unconditioned.operation
    assert conditional.conditional_on_success is True
    assert unconditioned.conditional_on_success is False
    assert retry.retry_time_included is True
    assert retry.retry_index == 2


def _benchmark_row(
    *,
    operation: str,
    sampling_condition: str,
    conditional_on_success: bool = False,
    retry_time_included: bool = False,
    retry_index: int = 0,
) -> LCLABenchmarkRow:
    return LCLABenchmarkRow(
        protocol="LCLA-AKA",
        profile="toy",
        backend="numpy_reference",
        keygen_backend="constructed_relation",
        operation=operation,
        phase="full_handshake",
        repetition=0,
        seed=1,
        elapsed_ns=10,
        success=False,
        error_code="NOT_INTENDED_RECEIVER",
        measurement_kind="measured_failure",
        actual_execution_attempted=True,
        timeout_scope="",
        parent_attempt_id="test",
        git_commit="0" * 40,
        python_version="3.12",
        numpy_version="2.2",
        compiler="test",
        cpu="test",
        os="test",
        timestamp_utc="2026-01-01T00:00:00+00:00",
        distribution_variant="proof_consistent_small_secret",
        sampling_condition=sampling_condition,
        retry_index=retry_index,
        conditional_on_success=conditional_on_success,
        retry_time_included=retry_time_included,
    )


def test_final_validator_separates_accepted_consistency_from_honest_correctness() -> None:
    evidence = validate_lcla_full(repo_root=ROOT, mode="smoke")

    assert str(evidence["result"]).startswith("partial_reproduction_observed_correctness_failure")
    assert evidence["accepted_session_consistency"] is True
    assert evidence["honest_execution_correctness_reproduced"] is False
    assert evidence["paper_correctness_claim_reproduced"] is False
    assert evidence["conditional_accepted_path_smoke"] is True
    assert evidence["lemma3_universal_correctness"] is False
    assert evidence["formal_security_verified"] is False
