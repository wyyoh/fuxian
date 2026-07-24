"""生成 C2LAKE 完整复现统一 evidence。"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import cast

import numpy as np
import numpy.typing as npt
import yaml

from lattice_aka_repro.c2lake_core import (
    C2LakeCoreError,
    C2LakeKeyPair,
    C2LakeMasterSecret,
    C2LakePublicParameters,
    extract_partial_private_key,
    set_secret_value,
    setup,
    verify_and_assemble_key,
)
from lattice_aka_repro.c2lake_cost_model import build_cost_tables
from lattice_aka_repro.c2lake_protocol import (
    C2LakeRequest,
    C2LakeResponse,
    C2LakeTimestampPolicy,
    initiator_create_request,
    initiator_verify_and_finish,
    make_protocol_context,
    responder_verify_and_reply,
    run_handshake,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--mode", choices=("smoke", "full"), default="smoke")
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("artifacts/processed/C2LAKE/full_validation.json"),
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        default=Path("reports/c2lake_full_validation.md"),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = validate_c2lake_full(repo_root=args.repo_root, mode=args.mode)
    _write_json(payload, args.json_output)
    _write_report(payload, args.report_output)
    print(args.json_output)
    print(args.report_output)
    return 0 if payload["result"] == "pass" else 1


def validate_c2lake_full(*, repo_root: Path, mode: str) -> dict[str, object]:
    git_commit, git_dirty = _git_state(repo_root)
    paper_manifest = _read_yaml(repo_root / "papers" / "C2LAKE_MANIFEST.yaml")
    core_validation = _read_or_run_json(
        repo_root,
        repo_root / "artifacts" / "processed" / "T010" / "c2lake_core_validation.json",
        [sys.executable, "scripts/validate_c2lake_core.py", "--repo-root", "."],
    )
    security_audit = _read_or_run_json(
        repo_root,
        repo_root / "artifacts" / "processed" / "C2LAKE" / "security_audit.json",
        [sys.executable, "scripts/audit_c2lake_security_claims.py", "--repo-root", "."],
    )
    protocol = _run_protocol_smoke(mode)
    benchmark_status = _benchmark_status(
        repo_root / "artifacts" / "processed" / "C2LAKE" / "table7_reproduced.csv"
    )
    cost_payload = build_cost_tables(specs_dir=repo_root / "specs")
    cost_model_status = {
        "result": cost_payload["result"],
        "communication_rows": len(cast(list[object], cost_payload["communication"])),
        "storage_rows": len(cast(list[object], cost_payload["storage"])),
        "operation_rows": len(cast(list[object], cost_payload["operations"])),
    }
    result = "pass"
    failure_reasons: list[str] = []
    if core_validation.get("result") != "pass":
        result = "fail"
        failure_reasons.append("core_validation_failed")
    if security_audit.get("result") != "pass":
        result = "fail"
        failure_reasons.append("security_audit_failed")
    if not protocol["protocol_correctness"]:
        result = "fail"
        failure_reasons.append("protocol_correctness_failed")
    if benchmark_status["status"] not in {"complete", "partial"}:
        result = "fail"
        failure_reasons.append("benchmark_status_invalid")
    return {
        "schema_version": 1,
        "result": result,
        "failure_reasons": failure_reasons,
        "git_commit": git_commit,
        "git_dirty": git_dirty,
        "paper_sha256": paper_manifest["sha256"],
        "core_validation": {
            "result": core_validation.get("result"),
            "failed_cases": core_validation.get("failed_cases"),
        },
        "independent_formula_check": core_validation.get("independent_formula_check", {}),
        "protocol_correctness": protocol["protocol_correctness"],
        "failed_protocol_cases": protocol["failed_protocol_cases"],
        "profile_session_counts": protocol["profile_session_counts"],
        "K1_consistency": protocol["K1_consistency"],
        "K2_consistency": protocol["K2_consistency"],
        "K3_consistency": protocol["K3_consistency"],
        "session_key_consistency": protocol["session_key_consistency"],
        "negative_test_matrix": protocol["negative_test_matrix"],
        "timestamp_test_matrix": protocol["timestamp_test_matrix"],
        "replay_test_matrix": protocol["replay_test_matrix"],
        "cost_model_status": cost_model_status,
        "benchmark_status": benchmark_status["status"],
        "completed_benchmark_profiles": benchmark_status["completed_profiles"],
        "incomplete_benchmark_profiles": benchmark_status["incomplete_profiles"],
        "security_claims_executable": _security_summary(security_audit)["executable_claims"],
        "security_claims_paper_only": _security_summary(security_audit)["paper_only_claims"],
        "eck_formally_verified": False,
        "rom_reduction_verified": False,
        "isis_hardness_verified": False,
        "cbi_isis_hardness_verified": False,
    }


def _run_protocol_smoke(mode: str) -> dict[str, object]:
    counts = {"toy": 50, "paper_literal_m32": 5, "audited_prime_m32": 5}
    if mode == "full":
        counts = {"toy": 1_000, "paper_literal_m32": 100, "audited_prime_m32": 100}
    failed_protocol_cases = 0
    profile_session_counts: dict[str, int] = {}
    k1_ok = True
    k2_ok = True
    k3_ok = True
    session_key_ok = True
    for profile, count in counts.items():
        public_params, alice_key_pair, bob_key_pair = _fixture(profile)
        profile_session_counts[profile] = 0
        for offset in range(count):
            alice_result, bob_result = run_handshake(
                public_params,
                alice_key_pair,
                bob_key_pair,
                "alice@example.test",
                "bob@example.test",
                80_000 + offset,
                90_000 + offset,
                1_000,
                1_001,
                1_001,
                C2LakeTimestampPolicy(max_clock_skew=10, max_message_age=60),
            )
            profile_session_counts[profile] += 1
            k1_ok = k1_ok and alice_result.components.k1 == bob_result.components.k1
            k2_ok = k2_ok and alice_result.components.k2 == bob_result.components.k2
            k3_ok = k3_ok and alice_result.components.k3 == bob_result.components.k3
            session_key_ok = session_key_ok and (
                alice_result.session_key_scalar == bob_result.session_key_scalar
                and alice_result.session_key_bytes == bob_result.session_key_bytes
            )
    negative = _negative_test_matrix()
    timestamps = _timestamp_test_matrix()
    replay = _replay_test_matrix()
    failed_protocol_cases += sum(not passed for passed in negative.values())
    failed_protocol_cases += sum(not passed for passed in timestamps.values())
    failed_protocol_cases += sum(not passed for passed in replay.values())
    protocol_correctness = (
        failed_protocol_cases == 0 and k1_ok and k2_ok and k3_ok and session_key_ok
    )
    return {
        "protocol_correctness": protocol_correctness,
        "failed_protocol_cases": failed_protocol_cases,
        "profile_session_counts": profile_session_counts,
        "K1_consistency": k1_ok,
        "K2_consistency": k2_ok,
        "K3_consistency": k3_ok,
        "session_key_consistency": session_key_ok,
        "negative_test_matrix": negative,
        "timestamp_test_matrix": timestamps,
        "replay_test_matrix": replay,
    }


def _negative_test_matrix() -> dict[str, bool]:
    public_params, alice_key_pair, bob_key_pair = _fixture("toy")
    alice_context = make_protocol_context(public_params, alice_key_pair, "alice@example.test")
    bob_context = make_protocol_context(public_params, bob_key_pair, "bob@example.test")
    request, state = initiator_create_request(
        alice_context,
        bob_context.identity,
        timestamp=1_000,
        seed=101,
    )
    response, _responder_state, _bob_result = responder_verify_and_reply(
        bob_context,
        request,
        timestamp=1_001,
        seed=102,
        now=1_001,
        timestamp_policy=C2LakeTimestampPolicy(max_clock_skew=10, max_message_age=60),
    )
    results: dict[str, bool] = {}
    for field_name in ("ID_i", "P_i0", "P_i1", "X_i", "Y_i", "Z_i", "S_i", "T_i"):
        results[f"request:{field_name}"] = _raises_code(
            cast(
                Callable[[], object],
                lambda field=field_name: responder_verify_and_reply(
                    bob_context,
                    _tamper_request(request, field),
                    timestamp=1_001,
                    seed=103,
                    now=1_001,
                    timestamp_policy=C2LakeTimestampPolicy(max_clock_skew=10, max_message_age=60),
                ),
            ),
            "INVALID_INITIATOR_AUTH",
        )
    for field_name in ("ID_j", "P_j0", "P_j1", "X_j", "Y_j", "Z_j", "S_j", "T_j"):
        results[f"response:{field_name}"] = _raises_code(
            cast(
                Callable[[], object],
                lambda field=field_name: initiator_verify_and_finish(
                    alice_context,
                    request,
                    state,
                    _tamper_response(response, field),
                    now=1_001,
                    timestamp_policy=C2LakeTimestampPolicy(max_clock_skew=10, max_message_age=60),
                ),
            ),
            "INVALID_RESPONDER_AUTH",
        )
    return results


def _timestamp_test_matrix() -> dict[str, bool]:
    public_params, alice_key_pair, bob_key_pair = _fixture("toy")
    alice_context = make_protocol_context(public_params, alice_key_pair, "alice@example.test")
    bob_context = make_protocol_context(public_params, bob_key_pair, "bob@example.test")
    policy = C2LakeTimestampPolicy(max_clock_skew=10, max_message_age=100)
    results: dict[str, bool] = {}
    for name, timestamp in (
        ("normal", 950),
        ("max_age_boundary", 900),
        ("future_boundary", 1_010),
    ):
        request, _state = initiator_create_request(
            alice_context,
            bob_context.identity,
            timestamp=timestamp,
            seed=200 + timestamp,
        )
        try:
            responder_verify_and_reply(
                bob_context,
                request,
                timestamp=1_000,
                seed=300 + timestamp,
                now=1_000,
                timestamp_policy=policy,
            )
            results[name] = True
        except C2LakeCoreError:
            results[name] = False
    for name, timestamp, code in (
        ("just_over_max_age", 899, "MESSAGE_EXPIRED"),
        ("future_over_skew", 1_011, "TIMESTAMP_IN_FUTURE"),
    ):
        request, _state = initiator_create_request(
            alice_context,
            bob_context.identity,
            timestamp=timestamp,
            seed=400 + timestamp,
        )
        results[name] = _raises_code(
            cast(
                Callable[[], object],
                lambda req=request: responder_verify_and_reply(
                    bob_context,
                    req,
                    timestamp=1_000,
                    seed=500,
                    now=1_000,
                    timestamp_policy=policy,
                ),
            ),
            code,
        )
    return results


def _replay_test_matrix() -> dict[str, bool]:
    public_params, alice_key_pair, bob_key_pair = _fixture("toy")
    alice_context = make_protocol_context(public_params, alice_key_pair, "alice@example.test")
    bob_context = make_protocol_context(public_params, bob_key_pair, "bob@example.test")
    policy = C2LakeTimestampPolicy(max_clock_skew=10, max_message_age=100)
    request, state = initiator_create_request(
        alice_context,
        bob_context.identity,
        timestamp=1_000,
        seed=601,
    )
    response, _responder_state, _bob_result = responder_verify_and_reply(
        bob_context,
        request,
        timestamp=1_000,
        seed=602,
        now=1_000,
        timestamp_policy=policy,
    )
    return {
        "replayed_old_request": _raises_code(
            lambda: responder_verify_and_reply(
                bob_context,
                request,
                timestamp=1_000,
                seed=603,
                now=1_101,
                timestamp_policy=policy,
            ),
            "MESSAGE_EXPIRED",
        ),
        "replayed_old_response": _raises_code(
            lambda: initiator_verify_and_finish(
                alice_context,
                request,
                state,
                response,
                now=1_101,
                timestamp_policy=policy,
            ),
            "MESSAGE_EXPIRED",
        ),
    }


def _fixture(profile: str) -> tuple[C2LakePublicParameters, C2LakeKeyPair, C2LakeKeyPair]:
    public_params, master_secret = setup(profile, seed=70_000, backend="safe")
    alice = _make_key_pair(public_params, master_secret, "alice@example.test", 70_001, 70_002)
    bob = _make_key_pair(public_params, master_secret, "bob@example.test", 70_003, 70_004)
    return public_params, alice, bob


def _make_key_pair(
    public_params: C2LakePublicParameters,
    master_secret: C2LakeMasterSecret,
    identity: str,
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


def _raises_code(callable_: Callable[[], object], code: str) -> bool:
    try:
        callable_()
    except C2LakeCoreError as error:
        return error.code == code
    return False


def _tamper_request(request: C2LakeRequest, field_name: str) -> C2LakeRequest:
    if field_name == "ID_i":
        return _replace_request(request, identity=b"mallory@example.test")
    if field_name == "P_i0":
        return _replace_request(request, p_i0=_tamper_vector(request.p_i0, request.q))
    if field_name == "P_i1":
        return _replace_request(request, p_i1=_tamper_vector(request.p_i1, request.q))
    if field_name == "X_i":
        return _replace_request(request, x_i_public=_tamper_vector(request.x_i_public, request.q))
    if field_name == "Y_i":
        return _replace_request(request, y_i_public=_tamper_vector(request.y_i_public, request.q))
    if field_name == "Z_i":
        return _replace_request(request, z_i_public=_tamper_vector(request.z_i_public, request.q))
    if field_name == "S_i":
        return _replace_request(request, s_i=_tamper_vector(request.s_i, request.q))
    if field_name == "T_i":
        return _replace_request(request, timestamp=request.timestamp + 1)
    raise AssertionError(field_name)


def _tamper_response(response: C2LakeResponse, field_name: str) -> C2LakeResponse:
    if field_name == "ID_j":
        return _replace_response(response, identity=b"mallory@example.test")
    if field_name == "P_j0":
        return _replace_response(response, p_j0=_tamper_vector(response.p_j0, response.q))
    if field_name == "P_j1":
        return _replace_response(response, p_j1=_tamper_vector(response.p_j1, response.q))
    if field_name == "X_j":
        return _replace_response(
            response, x_j_public=_tamper_vector(response.x_j_public, response.q)
        )
    if field_name == "Y_j":
        return _replace_response(
            response, y_j_public=_tamper_vector(response.y_j_public, response.q)
        )
    if field_name == "Z_j":
        return _replace_response(
            response, z_j_public=_tamper_vector(response.z_j_public, response.q)
        )
    if field_name == "S_j":
        return _replace_response(response, s_j=_tamper_vector(response.s_j, response.q))
    if field_name == "T_j":
        return _replace_response(response, timestamp=response.timestamp + 1)
    raise AssertionError(field_name)


def _replace_request(request: C2LakeRequest, **overrides: object) -> C2LakeRequest:
    values = {
        "identity": request.identity,
        "q": request.q,
        "profile": request.profile,
        "backend": request.backend,
        "n": request.n,
        "p_i0": request.p_i0,
        "p_i1": request.p_i1,
        "x_i_public": request.x_i_public,
        "y_i_public": request.y_i_public,
        "z_i_public": request.z_i_public,
        "s_i": request.s_i,
        "timestamp": request.timestamp,
    }
    values.update(overrides)
    return C2LakeRequest(**values)  # type: ignore[arg-type]


def _replace_response(response: C2LakeResponse, **overrides: object) -> C2LakeResponse:
    values = {
        "identity": response.identity,
        "q": response.q,
        "profile": response.profile,
        "backend": response.backend,
        "n": response.n,
        "p_j0": response.p_j0,
        "p_j1": response.p_j1,
        "x_j_public": response.x_j_public,
        "y_j_public": response.y_j_public,
        "z_j_public": response.z_j_public,
        "s_j": response.s_j,
        "timestamp": response.timestamp,
    }
    values.update(overrides)
    return C2LakeResponse(**values)  # type: ignore[arg-type]


def _tamper_vector(vector: npt.NDArray[np.int64], q: int) -> npt.NDArray[np.int64]:
    tampered = vector.copy()
    tampered[0] = (int(tampered[0]) + 1) % q
    return tampered


def _benchmark_status(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {"status": "missing", "completed_profiles": [], "incomplete_profiles": []}
    completed: set[str] = set()
    incomplete: set[str] = set()
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["phase"] != "full_handshake":
                continue
            if row["completed"] == "True":
                completed.add(row["profile"])
            else:
                incomplete.add(row["profile"])
    status = "complete" if completed and not incomplete else "partial" if completed else "missing"
    return {
        "status": status,
        "completed_profiles": sorted(completed),
        "incomplete_profiles": sorted(incomplete),
    }


def _read_or_run_json(repo_root: Path, path: Path, command: list[str]) -> dict[str, object]:
    if not path.is_file():
        subprocess.run(command, cwd=repo_root, check=True)
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def _read_yaml(path: Path) -> dict[str, object]:
    return cast(dict[str, object], yaml.safe_load(path.read_text(encoding="utf-8")))


def _security_summary(payload: dict[str, object]) -> dict[str, object]:
    return cast(dict[str, object], payload["summary"])


def _git_state(repo_root: Path) -> tuple[str, bool]:
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        text=True,
    ).strip()
    dirty = bool(
        subprocess.check_output(
            ["git", "status", "--porcelain=v1"],
            cwd=repo_root,
            text=True,
        ).strip()
    )
    return commit, dirty


def _write_json(payload: dict[str, object], output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output


def _write_report(payload: dict[str, object], output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# C2LAKE Full Validation",
        "",
        f"- result: {payload['result']}",
        f"- git_commit: {payload['git_commit']}",
        f"- git_dirty: {payload['git_dirty']}",
        f"- protocol_correctness: {payload['protocol_correctness']}",
        f"- failed_protocol_cases: {payload['failed_protocol_cases']}",
        f"- K1_consistency: {payload['K1_consistency']}",
        f"- K2_consistency: {payload['K2_consistency']}",
        f"- K3_consistency: {payload['K3_consistency']}",
        f"- session_key_consistency: {payload['session_key_consistency']}",
        f"- benchmark_status: {payload['benchmark_status']}",
        "- eck_formally_verified: false",
        "- rom_reduction_verified: false",
        "",
    ]
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


if __name__ == "__main__":
    raise SystemExit(main())
