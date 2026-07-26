#!/usr/bin/env python3
"""生成 LCLA-AKA 完整复现统一 evidence。"""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import fields, replace
from pathlib import Path
from typing import cast

import numpy as np
import numpy.typing as npt
import yaml

from lattice_aka_repro.lcla_backends import (
    generate_static_key_pair,
    load_lcla_profile,
    setup_lcla,
    verify_static_key,
)
from lattice_aka_repro.lcla_protocol import (
    LCLAHandshakeTrace,
    alice_finish,
    bob_finish,
    bob_respond,
    make_lcla_context,
    run_lcla_handshake,
    validate_session_pair,
)
from lattice_aka_repro.lcla_types import (
    LCLAAliceFinish,
    LCLAAliceRequest,
    LCLABobResponse,
    LCLAError,
    LCLAProtocolContext,
    LCLAStaticKeyPair,
)

_OBSERVED_FAILURE = (
    "partial_reproduction_observed_correctness_failure_constructed_backend_unverified_security"
)
_REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--mode", choices=("smoke", "full"), default="smoke")
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("artifacts/processed/LCLA_AKA/full_validation.json"),
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        default=Path("reports/lcla_aka_full_validation.md"),
    )
    parser.add_argument(
        "--correctness-input",
        type=Path,
        default=Path("artifacts/processed/LCLA_AKA/unconditioned_correctness_summary.json"),
    )
    parser.add_argument(
        "--correctness-benchmark-input",
        type=Path,
        default=Path(
            "artifacts/processed/LCLA_AKA/correctness_patch_benchmark_summary.json"
        ),
    )
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    payload = validate_lcla_full(
        repo_root=repo_root,
        mode=args.mode,
        correctness_path=_resolve(repo_root, args.correctness_input),
        correctness_benchmark_path=_resolve(
            repo_root,
            args.correctness_benchmark_input,
        ),
    )
    json_output = _resolve(repo_root, args.json_output)
    report_output = _resolve(repo_root, args.report_output)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_output.write_text(render_report(payload), encoding="utf-8")
    print(json.dumps({"result": payload["result"], "output": str(json_output)}))
    return 0 if payload["executable_validation_passed"] is True else 1


def validate_lcla_full(
    *,
    repo_root: Path,
    mode: str,
    correctness_path: Path | None = None,
    correctness_benchmark_path: Path | None = None,
) -> dict[str, object]:
    """执行轻量协议/攻击检查并聚合已提交证据。"""

    if mode not in {"smoke", "full"}:
        raise ValueError("mode 必须为 smoke 或 full")
    git_commit, git_dirty = _git_state(repo_root)
    manifest = _read_yaml(repo_root / "papers" / "LCLA_AKA_MANIFEST.yaml")
    dependency = _read_json(
        repo_root / "artifacts" / "processed" / "LCLA_AKA" / "dependency_capabilities.json"
    )
    security = _read_json(
        repo_root / "artifacts" / "processed" / "LCLA_AKA" / "security_audit.json"
    )
    reproduction = _read_json(
        repo_root / "artifacts" / "processed" / "LCLA_AKA" / "reproduction_summary.json"
    )
    correctness = _read_json(
        correctness_path
        if correctness_path is not None
        else (
            repo_root
            / "artifacts"
            / "processed"
            / "LCLA_AKA"
            / "unconditioned_correctness_summary.json"
        )
    )
    correctness_benchmark = _read_json(
        correctness_benchmark_path
        if correctness_benchmark_path is not None
        else (
            repo_root
            / "artifacts"
            / "processed"
            / "LCLA_AKA"
            / "correctness_patch_benchmark_summary.json"
        )
    )
    protocol = _conditional_path_smoke()
    intended = cast(list[dict[str, object]], correctness["intended_recipient_statistics"])
    tamper = _tamper_matrix()
    costs = _read_json(repo_root / "artifacts" / "processed" / "LCLA_AKA" / "cost_tables.json")
    table_iv = _read_json(
        repo_root / "artifacts" / "processed" / "LCLA_AKA" / "table_iv_summary.json"
    )
    table_v = _read_json(
        repo_root / "artifacts" / "processed" / "LCLA_AKA" / "table_v_summary.json"
    )
    figure4 = _read_json(
        repo_root / "artifacts" / "processed" / "LCLA_AKA" / "figure4_summary.json"
    )
    figure5 = _read_json(
        repo_root / "artifacts" / "processed" / "LCLA_AKA" / "figure5_formulas.json"
    )
    figure6 = _read_json(
        repo_root / "artifacts" / "processed" / "LCLA_AKA" / "figure6_formulas.json"
    )
    aggregate = cast(dict[str, object], correctness["aggregate"])
    accepted_consistency = bool(correctness["accepted_session_consistency"])
    honest_correctness = bool(correctness["honest_execution_correctness_reproduced"])
    paper_correctness = bool(correctness["paper_correctness_claim_reproduced"])
    failed_protocol_cases = int(cast(int, aggregate["other_failure"]))
    executable_validation_passed = bool(
        protocol["conditional_accepted_path_smoke"] is True
        and accepted_consistency
        and failed_protocol_cases == 0
        and all(tamper.values())
        and security["formal_security_verified"] is False
    )
    backend_complete = bool(
        dependency["frodo_native_lcla_backend_available"] is True
        and dependency["real_trapdoor_backend_status"] == "available"
        and dependency["sample_pre_status"] == "available"
    )
    result = "fail" if not executable_validation_passed else _OBSERVED_FAILURE
    matrix = cast(list[dict[str, object]], correctness["matrix"])
    counts = {f"{row['profile']}:{row['distribution_variant']}": row for row in matrix}
    return {
        "schema_version": 2,
        "result": result,
        "git_commit": git_commit,
        "git_dirty": git_dirty,
        "paper_sha256": manifest["sha256"],
        "profile_validation": True,
        "dependency_capabilities": dependency["capabilities"],
        "frodo_status": {
            "identified": dependency["paper_frodo_backend_identified"],
            "built": dependency["paper_frodo_backend_built"],
            "native_lcla_available": dependency["frodo_native_lcla_backend_available"],
        },
        "trapdoor_backend_status": dependency["real_trapdoor_backend_status"],
        "sample_pre_status": dependency["sample_pre_status"],
        "programmed_h1_used": True,
        "distribution_variants": correctness["distribution_variants"],
        "correctness_benchmark_distribution_variants": correctness_benchmark[
            "distribution_variants"
        ],
        "correctness_benchmark_status": correctness_benchmark["result"],
        "correctness_benchmark_raw_sha256": correctness_benchmark["raw_sha256"],
        "correctness_benchmark_raw_row_count": correctness_benchmark["raw_row_count"],
        "conditional_success_path_latency_is_not_table_v_equivalent": correctness_benchmark[
            "conditional_success_path_latency_is_not_table_v_equivalent"
        ],
        "static_relation_correctness": correctness["static_relation_correctness"],
        "static_relation_constructed": True,
        "definition5_literal_implemented": correctness["definition5_literal_implemented"],
        "lemma3_counterexample_found": correctness["lemma3_counterexample_found"],
        "lemma3_universal_correctness": correctness["lemma3_universal_correctness"],
        "paper_correctness_proof_supported": correctness["paper_correctness_proof_supported"],
        "reconciliation_status": correctness["definition5_literal_implemented"],
        "reconciliation_failure_counts": {
            key: row["final_reconciliation_failure_count"] for key, row in counts.items()
        },
        "protocol_correctness": False,
        "accepted_session_consistency": accepted_consistency,
        "honest_execution_correctness_reproduced": honest_correctness,
        "paper_correctness_claim_reproduced": paper_correctness,
        "honest_execution_attempts": aggregate["honest_execution_attempts"],
        "honest_execution_accepted": aggregate["honest_execution_accepted"],
        "honest_execution_acceptance_rate": aggregate["honest_execution_acceptance_rate"],
        "first_stage_false_reject_count": aggregate["first_stage_false_reject_count"],
        "final_reconciliation_failure_count": aggregate["final_reconciliation_failure_count"],
        "failed_protocol_cases": failed_protocol_cases,
        "profile_session_counts": counts,
        "documented_legacy_profile_attempts": reproduction["protocol_attempts"],
        "intended_receiver_filtering": intended,
        "conditional_accepted_path_smoke": protocol["conditional_accepted_path_smoke"],
        "conditional_path_seed_selection_used": True,
        "m1_consistency": accepted_consistency,
        "m2_consistency": accepted_consistency,
        "session_key_consistency": accepted_consistency,
        "identity_recovery": accepted_consistency,
        "plaintext_identity_round1": False,
        "plaintext_identity_round2": False,
        "identity_masked_round3": True,
        "tamper_test_matrix": tamper,
        "cost_model_status": costs["result"],
        "table_iv_status": table_iv["result"],
        "table_v_status": table_v["result"],
        "figure4_status": figure4["result"],
        "figure5_status": figure5["result"],
        "figure6_status": figure6["result"],
        "strict_original_timing_reproduced": False,
        "real_trapdoor_reproduced": False,
        "real_trapdoor_static_keygen_reproduced": False,
        "constructed_protocol_reproduced": True,
        "executable_state_machine_implemented": True,
        "executable_validation_passed": executable_validation_passed,
        "benchmark_status": "partial",
        "backend_status": ("complete" if backend_complete else "partial_constructed_relation_only"),
        "formal_security_verified": False,
        "anonymity_formally_verified": False,
        "mbr_formally_verified": False,
        "lwe_reduction_verified": False,
        "isis_hardness_verified": False,
        "quantum_security_verified": False,
        "paper_security_proof_reproduced": False,
        "malicious_kgc_security_reproduced": False,
        "mode": mode,
    }


def _conditional_path_smoke() -> dict[str, object]:
    context, alice, bob, trace = _find_conditional_fixture("paper_performance")
    static_ok = verify_static_key(context.parameters, alice) and verify_static_key(
        context.parameters, bob
    )
    consistent = bool(
        trace.m1_consistency
        and trace.m2_consistency
        and trace.session_key_consistency
        and trace.alice_result.local_identity == trace.bob_result.peer_identity
    )
    return {
        "static_relation_correctness": static_ok,
        "conditional_accepted_path_smoke": static_ok and consistent,
        "seed_selection_used": True,
    }


def _find_conditional_fixture(
    profile_name: str,
) -> tuple[LCLAProtocolContext, LCLAStaticKeyPair, LCLAStaticKeyPair, LCLAHandshakeTrace]:
    profile = load_lcla_profile(_REPO_ROOT, profile_name)
    parameters = setup_lcla(
        profile=profile,
        backend="fast",
        keygen_backend="constructed_relation",
        seed=41_000_000,
        distribution_variant="proof_consistent_small_secret",
    )
    alice = generate_static_key_pair(parameters, "Alice", seed=41_000_001)
    bob = generate_static_key_pair(parameters, "Bob", seed=41_000_002)
    context = make_lcla_context(parameters)
    for offset in range(5_000):
        try:
            trace = run_lcla_handshake(
                context,
                alice,
                bob,
                "Alice",
                "Bob",
                initiator_seed=41_010_000 + offset,
                responder_seed=41_100_000 + offset,
            )
        except LCLAError:
            continue
        return context, alice, bob, trace
    raise LCLAError("CONDITIONAL_SMOKE_UNAVAILABLE", "未找到仅用于攻击夹具的接受路径")


def _tamper_matrix() -> dict[str, bool]:
    context, alice, bob, trace = _find_conditional_fixture("paper_performance")
    q = context.profile.q
    results: dict[str, bool] = {}
    request_variants = {
        "request:C_A": replace(trace.request, c_a=_changed_zq(trace.request.c_a, q)),
        "request:delta_A": replace(trace.request, delta_a=_changed_bit(trace.request.delta_a)),
        "request:h_A": replace(trace.request, h_a=_changed_bit(trace.request.h_a)),
    }
    for name, request in request_variants.items():
        results[name] = _raises_code(
            lambda request=request: bob_respond(
                context,
                bob,
                "Bob",
                request,
                seed=70_001,
            ),
            {"NOT_INTENDED_RECEIVER"},
        )
    initial_state = replace(
        trace.alice_state,
        e_b_vector=None,
        n_b_prime=None,
        m2=None,
    )
    response_variants = {
        "response:C_B": replace(trace.response, c_b=_changed_zq(trace.response.c_b, q)),
        "response:h_B": replace(trace.response, h_b=_changed_bit(trace.response.h_b)),
    }
    for name, response in response_variants.items():
        results[name] = _raises_code(
            lambda response=response: alice_finish(
                context,
                alice,
                "Alice",
                "Bob",
                trace.request,
                initial_state,
                response,
                seed=70_002,
            ),
            {"INVALID_RESPONDER_MAC"},
        )
    changed_t = bytearray(trace.finish.t_a)
    changed_t[0] ^= 1
    results["finish:T_A"] = _raises_code(
        lambda: bob_finish(
            context,
            bob,
            "Bob",
            trace.request,
            trace.response,
            trace.bob_state,
            replace(trace.finish, t_a=bytes(changed_t)),
        ),
        {"ID_RECOVERY_FAILURE"},
    )
    tampered_delta = replace(trace.finish, delta_b=_changed_bit(trace.finish.delta_b))
    try:
        bob_result = bob_finish(
            context,
            bob,
            "Bob",
            trace.request,
            trace.response,
            trace.bob_state,
            tampered_delta,
        )
    except LCLAError as exc:
        results["finish:delta_B"] = exc.code == "ID_RECOVERY_FAILURE"
    else:
        results["finish:delta_B"] = _raises_code(
            lambda: validate_session_pair(trace.alice_result, bob_result),
            {
                "ID_RECOVERY_FAILURE",
                "RECONCILIATION_FAILURE",
                "SESSION_KEY_MISMATCH",
                "TRANSCRIPT_MISMATCH",
            },
        )
    return results


def _raises_code(callback: object, codes: set[str]) -> bool:
    if not callable(callback):
        return False
    try:
        callback()
    except LCLAError as exc:
        return exc.code in codes
    return False


def _changed_zq(array: npt.NDArray[np.int64], q: int) -> npt.NDArray[np.int64]:
    changed = np.array(array, dtype=np.int64, copy=True)
    changed.flat[0] = (int(changed.flat[0]) + 1) % q
    return changed


def _changed_bit(array: npt.NDArray[np.int64]) -> npt.NDArray[np.int64]:
    changed = np.array(array, dtype=np.int64, copy=True)
    changed.flat[0] ^= 1
    return changed


def render_report(payload: dict[str, object]) -> str:
    return "\n".join(
        [
            "# LCLA-AKA Full Validation",
            "",
            f"- result: `{payload['result']}`",
            f"- executable_validation_passed: `{payload['executable_validation_passed']}`",
            f"- benchmark_status: `{payload['benchmark_status']}`",
            f"- backend_status: `{payload['backend_status']}`",
            f"- accepted_session_consistency: `{payload['accepted_session_consistency']}`",
            "- honest_execution_correctness_reproduced: "
            f"`{payload['honest_execution_correctness_reproduced']}`",
            "- paper_correctness_claim_reproduced: "
            f"`{payload['paper_correctness_claim_reproduced']}`",
            f"- lemma3_universal_correctness: `{payload['lemma3_universal_correctness']}`",
            f"- honest_execution_attempts: `{payload['honest_execution_attempts']}`",
            f"- honest_execution_accepted: `{payload['honest_execution_accepted']}`",
            f"- formal_security_verified: `{payload['formal_security_verified']}`",
            "",
            "`executable_validation_passed=true` 只表示状态机、constructed relation、条件接受",
            "路径与篡改夹具可执行。它不表示诚实执行达到论文的高概率正确性主张。",
            "无条件连续 seed 试验、目标误拒绝和 Lemma 3 素数 q 反例均独立保留。",
            "",
        ]
    )


def _read_json(path: Path) -> dict[str, object]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path} 顶层必须为 object")
    return cast(dict[str, object], raw)


def _read_yaml(path: Path) -> dict[str, object]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path} 顶层必须为 mapping")
    return cast(dict[str, object], raw)


def _git_state(repo_root: Path) -> tuple[str, bool]:
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        text=True,
    ).strip()
    dirty = bool(
        subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            text=True,
        ).strip()
    )
    return commit, dirty


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def public_packet_field_counts() -> tuple[int, int, int]:
    """供测试锁定三轮 packet 的公开协议字段数（不含上下文元数据）。"""

    excluded = {"q", "profile", "backend"}
    counts = tuple(
        len({field.name for field in fields(packet)} - excluded)
        for packet in (LCLAAliceRequest, LCLABobResponse, LCLAAliceFinish)
    )
    return cast(tuple[int, int, int], counts)


if __name__ == "__main__":
    raise SystemExit(main())
