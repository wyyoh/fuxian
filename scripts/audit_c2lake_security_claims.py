"""生成 C2LAKE Section 6 安全主张审计 evidence。

该脚本只审计主张覆盖、证据边界和已知论文歧义；不会形式化验证 eCK、ROM、
forking lemma、ISIS 或 CBi-ISIS 归约。
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Final, cast

import yaml

_REQUIRED_CLAIMS: Final = (
    "correctness",
    "mutual_authentication",
    "session_key_agreement",
    "replay_resistance",
    "impersonation_resistance",
    "man_in_the_middle_resistance",
    "known_key_security",
    "unknown_key_share_resistance",
    "no_key_control",
    "perfect_forward_secrecy",
    "known_session_key_security",
    "type_i_adversary_proof",
    "type_ii_adversary_proof",
    "isis_reduction",
    "cbi_isis_reduction",
)
_ALLOWED_STATUSES: Final = frozenset(
    {
        "executable_checked",
        "algebraically_checked",
        "paper_proof_only",
        "not_formally_verified",
        "out_of_scope",
    }
)
_REQUIRED_ISSUES: Final = (
    "matrix_dimension_conflict",
    "q_prime_vs_m_squared",
    "h2_h3_local_field_typos",
    "theorem_1_sk_label_typo",
    "short_vector_bound_unclear",
    "key_agreement_timing_boundary_unspecified",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("artifacts/processed/C2LAKE/security_audit.json"),
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        default=Path("reports/c2lake_security_audit.md"),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = audit_security_claims(repo_root=args.repo_root)
    _write_json(payload, args.json_output)
    _write_report(payload, args.report_output)
    print(args.json_output)
    print(args.report_output)
    return 0 if payload["result"] == "pass" else 1


def audit_security_claims(*, repo_root: Path) -> dict[str, object]:
    obligations = _read_yaml(repo_root / "specs" / "c2lake" / "proof_obligations.yaml")
    manifest = _read_yaml(repo_root / "papers" / "C2LAKE_MANIFEST.yaml")
    claims = _read_claims(obligations)
    issues = _read_issues(obligations)
    errors = _validate_claims_and_issues(claims, issues)
    git_commit, git_dirty = _git_state(repo_root)
    status_counts: dict[str, int] = {status: 0 for status in sorted(_ALLOWED_STATUSES)}
    for claim in claims:
        status_counts[cast(str, claim["status"])] += 1
    executable_claims = [
        cast(str, claim["id"]) for claim in claims if claim["status"] == "executable_checked"
    ]
    paper_only_claims = [
        cast(str, claim["id"])
        for claim in claims
        if claim["status"] in {"paper_proof_only", "not_formally_verified"}
    ]
    payload: dict[str, object] = {
        "schema_version": 1,
        "result": "pass" if not errors else "fail",
        "git_commit": git_commit,
        "git_dirty": git_dirty,
        "paper": obligations["paper"],
        "paper_sha256": manifest["sha256"],
        "claims": claims,
        "known_issues": issues,
        "summary": {
            "claim_count": len(claims),
            "known_issue_count": len(issues),
            "status_counts": status_counts,
            "executable_claims": executable_claims,
            "paper_only_claims": paper_only_claims,
        },
        "explicit_boundaries": {
            "correctness_executable_checked": "correctness" in executable_claims,
            "tamper_and_replay_are_attack_simulations": True,
            "eck_formally_verified": False,
            "rom_reduction_verified": False,
            "forking_lemma_formally_verified": False,
            "isis_hardness_verified": False,
            "cbi_isis_hardness_verified": False,
            "paper_security_proof_reproduced": False,
        },
        "errors": errors,
    }
    return payload


def _read_yaml(path: Path) -> dict[str, object]:
    raw: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path} 顶层必须是映射")
    return cast(dict[str, object], raw)


def _read_claims(obligations: dict[str, object]) -> list[dict[str, object]]:
    raw_claims = obligations.get("claims")
    if not isinstance(raw_claims, list):
        raise ValueError("proof_obligations.yaml claims 必须是列表")
    claims: list[dict[str, object]] = []
    for raw_claim in raw_claims:
        if not isinstance(raw_claim, dict):
            raise ValueError("每个 claim 必须是映射")
        claims.append(cast(dict[str, object], raw_claim))
    return claims


def _read_issues(obligations: dict[str, object]) -> list[dict[str, object]]:
    raw_issues = obligations.get("known_issues")
    if not isinstance(raw_issues, list):
        raise ValueError("proof_obligations.yaml known_issues 必须是列表")
    issues: list[dict[str, object]] = []
    for raw_issue in raw_issues:
        if not isinstance(raw_issue, dict):
            raise ValueError("每个 known issue 必须是映射")
        issues.append(cast(dict[str, object], raw_issue))
    return issues


def _validate_claims_and_issues(
    claims: list[dict[str, object]],
    issues: list[dict[str, object]],
) -> list[dict[str, object]]:
    errors: list[dict[str, object]] = []
    claim_ids = {claim.get("id") for claim in claims}
    for claim_id in _REQUIRED_CLAIMS:
        if claim_id not in claim_ids:
            errors.append({"code": "CLAIM_MISSING", "claim_id": claim_id})
    for claim in claims:
        if claim.get("status") not in _ALLOWED_STATUSES:
            errors.append(
                {
                    "code": "CLAIM_STATUS_INVALID",
                    "claim_id": claim.get("id"),
                    "status": claim.get("status"),
                }
            )
        if claim.get("formally_verified") is not False:
            errors.append({"code": "FORMAL_VERIFICATION_FLAG_INVALID", "claim_id": claim.get("id")})
        evidence = claim.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append({"code": "CLAIM_EVIDENCE_MISSING", "claim_id": claim.get("id")})
    issue_ids = {issue.get("id") for issue in issues}
    for issue_id in _REQUIRED_ISSUES:
        if issue_id not in issue_ids:
            errors.append({"code": "KNOWN_ISSUE_MISSING", "issue_id": issue_id})
    return errors


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
    output.write_text(_render_report(payload), encoding="utf-8")
    return output


def _render_report(payload: dict[str, object]) -> str:
    claims = cast(list[dict[str, object]], payload["claims"])
    issues = cast(list[dict[str, object]], payload["known_issues"])
    boundaries = cast(dict[str, object], payload["explicit_boundaries"])
    lines = [
        "# C2LAKE Security Claim Audit",
        "",
        "## Summary",
        "",
        f"- result: {payload['result']}",
        f"- paper_sha256: {payload['paper_sha256']}",
        "- eck_formally_verified: false",
        "- rom_reduction_verified: false",
        "- isis_hardness_verified: false",
        "- cbi_isis_hardness_verified: false",
        "",
        "## Evidence Boundary",
        "",
        "- correctness 可通过代码执行路径与代数恒等式检查。",
        "- 消息篡改与重放只能作为攻击模拟测试。",
        "- eCK、ROM、forking lemma 与安全归约未做形式化验证。",
        "- 本审计不得解释为论文安全证明已复现成功。",
        "",
        "## Claim Matrix",
        "",
        "| claim_id | status | formally_verified |",
        "| --- | --- | --- |",
    ]
    for claim in claims:
        lines.append(f"| {claim['id']} | {claim['status']} | {claim['formally_verified']} |")
    lines.extend(
        [
            "",
            "## Known Paper Issues",
            "",
        ]
    )
    for issue in issues:
        lines.append(f"- {issue['id']}: {issue['issue']}")
    lines.extend(
        [
            "",
            "## Explicit Machine Flags",
            "",
            "```json",
            json.dumps(boundaries, ensure_ascii=False, allow_nan=False, indent=2, sort_keys=True),
            "```",
            "",
        ]
    )
    if payload["errors"]:
        lines.extend(["## Errors", "", "```json"])
        lines.append(json.dumps(payload["errors"], ensure_ascii=False, allow_nan=False, indent=2))
        lines.extend(["```", ""])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
