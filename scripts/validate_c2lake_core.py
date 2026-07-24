"""运行 T010 C2LAKE 核心 evidence 校验。"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import cast

import numpy as np
import numpy.typing as npt
import yaml

from lattice_aka_repro.c2lake_core import (
    C2LakeCoreError,
    C2LakePartialPrivateKey,
    C2LakePublicParameters,
    C2LakeUserSecret,
    bounded_ternary_vector,
    centered_norm,
    extract_partial_private_key,
    set_secret_value,
    setup,
    verify_and_assemble_key,
    verify_partial_key,
)
from lattice_aka_repro.evidence import collect_run_metadata
from lattice_aka_repro.randomness import seeded_rng

_PROFILES = ("toy", "paper_literal_m32", "audited_prime_m32")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--specs-dir", type=Path)
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--seed-count", type=int, default=100)
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("artifacts/processed/T010/c2lake_core_validation.json"),
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        default=Path("reports/c2lake_core_validation.md"),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_root = args.repo_root
    specs_dir = args.specs_dir if args.specs_dir is not None else repo_root / "specs"
    payload = validate_c2lake_core(
        repo_root=repo_root,
        specs_dir=specs_dir,
        seed_start=args.seed_start,
        seed_count=args.seed_count,
    )
    _write_json(payload, args.json_output)
    _write_report(payload, args.report_output)
    print(args.json_output)
    print(args.report_output)
    return 0 if payload["result"] == "pass" else 1


def validate_c2lake_core(
    *,
    repo_root: Path,
    specs_dir: Path,
    seed_start: int,
    seed_count: int,
) -> dict[str, object]:
    seeds = list(range(seed_start, seed_start + seed_count))
    metadata = collect_run_metadata(
        task_id="T010",
        profile="toy,paper_literal_m32,audited_prime_m32",
        backend="safe,fast",
        seed=seed_start,
        warmup=0,
        repetitions=seed_count,
        repo_root=repo_root,
    )
    manifest = _read_manifest(repo_root / "papers" / "C2LAKE_MANIFEST.yaml")
    failed_case_details: list[dict[str, object]] = []
    profile_results = {
        profile: _run_profile_cases(profile, seeds, specs_dir, failed_case_details)
        for profile in _PROFILES
    }
    safe_fast_consistency = _safe_fast_consistency(specs_dir)
    if not safe_fast_consistency["passed"]:
        failed_case_details.append(
            {
                "case": "safe_fast_consistency",
                "profile": "toy",
                "reason": "safe 与 fast 后端结果不一致",
            }
        )
    bounded_norm_checks = _bounded_norm_checks(specs_dir, seeds, failed_case_details)
    negative_test_matrix = _negative_test_matrix(specs_dir)
    for field_name, passed in negative_test_matrix.items():
        if not passed:
            failed_case_details.append(
                {
                    "case": "negative_test_matrix",
                    "field": field_name,
                    "reason": "篡改后验证未失败",
                }
            )

    failed_cases = len(failed_case_details)
    result = "pass" if failed_cases == 0 else "fail"
    return {
        "schema_version": 1,
        "task_id": "T010",
        "result": result,
        "git_commit": metadata.git_commit,
        "git_dirty": metadata.git_dirty,
        "profile": "toy,paper_literal_m32,audited_prime_m32",
        "backend": "safe,fast",
        "seed_range": {
            "start": seed_start,
            "stop": seed_start + seed_count - 1,
            "count": seed_count,
        },
        "profile_results": profile_results,
        "failed_cases": failed_cases,
        "failed_case_details": failed_case_details,
        "safe_fast_consistency": safe_fast_consistency,
        "bounded_norm_checks": bounded_norm_checks,
        "negative_test_matrix": negative_test_matrix,
        "paper_manifest_sha256": manifest["sha256"],
        "paper_manifest": manifest,
        "protocol_key_agreement_implemented": False,
        "security_proof_verified": False,
        "metadata": asdict(metadata),
    }


def _run_profile_cases(
    profile: str,
    seeds: list[int],
    specs_dir: Path,
    failed_case_details: list[dict[str, object]],
) -> dict[str, object]:
    passed = 0
    failed = 0
    for seed in seeds:
        try:
            public_params, master_secret = setup(
                profile,
                seed=seed,
                backend="safe",
                specs_dir=specs_dir,
            )
            user_secret = set_secret_value(public_params, "alice@example.test", seed=10_000 + seed)
            partial_key = extract_partial_private_key(
                public_params,
                master_secret,
                "alice@example.test",
                user_secret.p_i1,
                seed=20_000 + seed,
            )
            verified = verify_partial_key(
                public_params,
                "alice@example.test",
                user_secret,
                partial_key,
            )
            verify_and_assemble_key(
                public_params,
                "alice@example.test",
                user_secret,
                partial_key,
            )
        except Exception as error:
            failed += 1
            failed_case_details.append(
                {
                    "case": "profile_100_seed_validation",
                    "profile": profile,
                    "seed": seed,
                    "reason": str(error),
                }
            )
            continue
        if verified:
            passed += 1
        else:
            failed += 1
            failed_case_details.append(
                {
                    "case": "profile_100_seed_validation",
                    "profile": profile,
                    "seed": seed,
                    "reason": "verify_partial_key returned false",
                }
            )
    return {"passed": passed, "failed": failed, "total": len(seeds)}


def _safe_fast_consistency(specs_dir: Path) -> dict[str, object]:
    safe_params, safe_master = setup("toy", seed=30_001, backend="safe", specs_dir=specs_dir)
    fast_params, fast_master = setup("toy", seed=30_001, backend="fast", specs_dir=specs_dir)
    safe_user = set_secret_value(safe_params, "alice@example.test", seed=30_002)
    fast_user = set_secret_value(fast_params, "alice@example.test", seed=30_002)
    safe_partial = extract_partial_private_key(
        safe_params,
        safe_master,
        "alice@example.test",
        safe_user.p_i1,
        seed=30_003,
    )
    fast_partial = extract_partial_private_key(
        fast_params,
        fast_master,
        "alice@example.test",
        fast_user.p_i1,
        seed=30_003,
    )
    checks = {
        "M": bool(np.array_equal(safe_params.matrix, fast_params.matrix)),
        "P": bool(np.array_equal(safe_params.public_key, fast_params.public_key)),
        "d": bool(np.array_equal(safe_master.vector, fast_master.vector)),
        "d_i1": bool(np.array_equal(safe_user.d_i1, fast_user.d_i1)),
        "P_i1": bool(np.array_equal(safe_user.p_i1, fast_user.p_i1)),
        "d_i0": bool(np.array_equal(safe_partial.d_i0, fast_partial.d_i0)),
        "P_i0": bool(np.array_equal(safe_partial.p_i0, fast_partial.p_i0)),
    }
    return {"profile": "toy", "passed": all(checks.values()), "checks": checks}


def _bounded_norm_checks(
    specs_dir: Path,
    seeds: list[int],
    failed_case_details: list[dict[str, object]],
) -> dict[str, object]:
    checked_vectors = 0
    max_norm = 0.0
    failures: list[dict[str, object]] = []
    for profile in ("toy", "audited_prime_m32"):
        public_params, master_secret = setup(
            profile,
            seed=40_000,
            backend="safe",
            specs_dir=specs_dir,
        )
        user_secret = set_secret_value(public_params, "alice@example.test", seed=40_001)
        vectors = {"d": master_secret.vector, "d_i1": user_secret.d_i1}
        for name, vector in vectors.items():
            checked_vectors += 1
            norm = centered_norm(vector, q=public_params.q)
            max_norm = max(max_norm, norm)
            if norm > public_params.beta:
                failure: dict[str, object] = {
                    "profile": profile,
                    "vector": name,
                    "norm": norm,
                    "beta": public_params.beta,
                }
                failures.append(failure)
                failed_case_details.append({"case": "bounded_norm", **failure})
    public_params, _ = setup("audited_prime_m32", seed=40_002, backend="safe", specs_dir=specs_dir)
    for seed in seeds:
        vector = bounded_ternary_vector(
            seeded_rng(50_000 + seed),
            public_params.n,
            q=public_params.q,
            beta=public_params.beta,
        )
        checked_vectors += 1
        norm = centered_norm(vector, q=public_params.q)
        max_norm = max(max_norm, norm)
        if norm > public_params.beta:
            failure = {
                "profile": "audited_prime_m32",
                "vector": "direct_sampler",
                "seed": seed,
                "norm": norm,
                "beta": public_params.beta,
            }
            failures.append(failure)
            failed_case_details.append({"case": "bounded_norm", **failure})
    return {
        "passed": not failures,
        "checked_vectors": checked_vectors,
        "max_norm": max_norm,
        "failures": failures,
    }


def _negative_test_matrix(specs_dir: Path) -> dict[str, bool]:
    public_params, master_secret = setup("toy", seed=60_000, backend="safe", specs_dir=specs_dir)
    identity = "alice@example.test"
    user_secret = set_secret_value(public_params, identity, seed=60_001)
    partial_key = extract_partial_private_key(
        public_params,
        master_secret,
        identity,
        user_secret.p_i1,
        seed=60_002,
    )
    tampered_params = C2LakePublicParameters(
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
    tampered_d_i0 = C2LakePartialPrivateKey(
        identity=partial_key.identity,
        q=partial_key.q,
        profile=partial_key.profile,
        backend=partial_key.backend,
        d_i0=_tamper_vector(partial_key.d_i0, partial_key.q),
        p_i0=partial_key.p_i0,
    )
    tampered_p_i0 = C2LakePartialPrivateKey(
        identity=partial_key.identity,
        q=partial_key.q,
        profile=partial_key.profile,
        backend=partial_key.backend,
        d_i0=partial_key.d_i0,
        p_i0=_tamper_vector(partial_key.p_i0, partial_key.q),
    )
    tampered_p_i1 = C2LakeUserSecret(
        identity=user_secret.identity,
        q=user_secret.q,
        profile=user_secret.profile,
        backend=user_secret.backend,
        d_i1=user_secret.d_i1,
        p_i1=_tamper_vector(user_secret.p_i1, user_secret.q),
    )
    return {
        "ID": not verify_partial_key(
            public_params,
            "mallory@example.test",
            user_secret,
            partial_key,
        ),
        "d_i0": not verify_partial_key(public_params, identity, user_secret, tampered_d_i0),
        "P_i0": not verify_partial_key(public_params, identity, user_secret, tampered_p_i0),
        "P_i1": not verify_partial_key(public_params, identity, tampered_p_i1, partial_key),
        "P": not verify_partial_key(tampered_params, identity, user_secret, partial_key),
    }


def _read_manifest(path: Path) -> dict[str, object]:
    raw: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise C2LakeCoreError("PROFILE_ERROR", "C2LAKE manifest 顶层必须是映射")
    manifest = cast(dict[object, object], raw)
    required = {
        "title": str,
        "doi": str,
        "sha256": str,
        "page_count": int,
        "relevant_pages": list,
        "local_file_tracked": bool,
    }
    output: dict[str, object] = {}
    for key, expected_type in required.items():
        value = manifest.get(key)
        if not isinstance(value, expected_type):
            raise C2LakeCoreError("PROFILE_ERROR", f"manifest 字段 {key!r} 类型错误")
        output[key] = value
    return output


def _tamper_vector(vector: npt.NDArray[np.int64], q: int) -> npt.NDArray[np.int64]:
    tampered = vector.copy()
    tampered[0] = (int(tampered[0]) + 1) % q
    return tampered


def _write_json(payload: dict[str, object], output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, allow_nan=False, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output


def _write_report(payload: dict[str, object], output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(_render_report(payload), encoding="utf-8")
    return output


def _render_report(payload: dict[str, object]) -> str:
    profile_results = cast(dict[str, dict[str, int]], payload["profile_results"])
    negative_matrix = cast(dict[str, bool], payload["negative_test_matrix"])
    safe_fast = cast(dict[str, object], payload["safe_fast_consistency"])
    bounded = cast(dict[str, object], payload["bounded_norm_checks"])
    lines = [
        "# C2LAKE Core Validation Report",
        "",
        "## Summary",
        "",
        f"- result: {payload['result']}",
        f"- failed_cases: {payload['failed_cases']}",
        f"- profiles: {payload['profile']}",
        f"- backend: {payload['backend']}",
        f"- paper_manifest_sha256: {payload['paper_manifest_sha256']}",
        "- protocol_key_agreement_implemented: false",
        "- security_proof_verified: false",
        "",
        "## Profile 100-seed validation",
        "",
        "| profile | passed | failed | total |",
        "| --- | ---: | ---: | ---: |",
    ]
    for profile in sorted(profile_results):
        result = profile_results[profile]
        lines.append(f"| {profile} | {result['passed']} | {result['failed']} | {result['total']} |")
    lines.extend(
        [
            "",
            "## Safe/Fast Consistency",
            "",
            f"- passed: {safe_fast['passed']}",
            "",
            "## Bounded Norm Checks",
            "",
            f"- passed: {bounded['passed']}",
            f"- checked_vectors: {bounded['checked_vectors']}",
            f"- max_norm: {bounded['max_norm']}",
            "",
            "## Negative Test Matrix",
            "",
            "| tampered field | verification failed |",
            "| --- | --- |",
        ]
    )
    for field_name in sorted(negative_matrix):
        lines.append(f"| {field_name} | {negative_matrix[field_name]} |")
    if payload["failed_case_details"]:
        lines.extend(["", "## Failed Case Details", ""])
        lines.append("```json")
        lines.append(
            json.dumps(
                payload["failed_case_details"],
                allow_nan=False,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        lines.append("```")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
