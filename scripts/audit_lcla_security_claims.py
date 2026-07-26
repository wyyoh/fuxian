#!/usr/bin/env python3
"""生成 LCLA-AKA 安全主张边界 evidence。"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import cast

import yaml


def audit(repo_root: Path) -> dict[str, object]:
    """加载 proof obligations 并验证所有 status。"""

    path = repo_root / "specs" / "lcla_aka" / "proof_obligations.yaml"
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("proof obligations 顶层必须为映射")
    allowed_raw = document.get("allowed_statuses")
    claims_raw = document.get("claims")
    flags_raw = document.get("machine_flags")
    ambiguities_raw = document.get("known_ambiguities")
    if not isinstance(allowed_raw, list) or not all(isinstance(item, str) for item in allowed_raw):
        raise ValueError("allowed_statuses 非法")
    if not isinstance(claims_raw, list) or not all(isinstance(item, dict) for item in claims_raw):
        raise ValueError("claims 非法")
    if not isinstance(flags_raw, dict):
        raise ValueError("machine_flags 非法")
    if not isinstance(ambiguities_raw, list) or not all(
        isinstance(item, dict)
        and isinstance(item.get("id"), str)
        and isinstance(item.get("summary"), str)
        for item in ambiguities_raw
    ):
        raise ValueError("known_ambiguities 非法")
    allowed = set(cast(list[str], allowed_raw))
    claims = cast(list[dict[str, object]], claims_raw)
    for claim in claims:
        if claim.get("status") not in allowed:
            raise ValueError(f"claim status 非法: {claim}")
    required_false = {
        "mbr_formally_verified",
        "lwe_reduction_verified",
        "isis_hardness_verified",
        "anonymity_formally_verified",
        "quantum_security_verified",
        "paper_security_proof_reproduced",
        "formal_security_verified",
        "malicious_kgc_security_reproduced",
    }
    flags = cast(dict[str, object], flags_raw)
    if any(flags.get(name) is not False for name in required_false):
        raise ValueError("形式安全边界 flag 必须保持 false")
    counts = Counter(str(claim["status"]) for claim in claims)
    return {
        "schema_version": 1,
        "result": "audit_complete_with_unverified_formal_security",
        "claim_count": len(claims),
        "status_counts": dict(sorted(counts.items())),
        "claims": claims,
        "known_ambiguities": ambiguities_raw,
        **flags,
    }


def render_report(evidence: dict[str, object]) -> str:
    """渲染简洁报告。"""

    claims = cast(list[dict[str, object]], evidence["claims"])
    lines = [
        "# LCLA-AKA 安全证明与主张审计",
        "",
        "## 结论",
        "",
        "状态机、静态代数关系和接受会话一致性可以执行检查，但无条件诚实执行",
        "未达到 0.999 正确性标准，Definition 5/Lemma 3 还存在素数 q 模回绕反例。",
        "身份未以明文字段出现在前两轮只属于结构检查。mBR、LWE/ISIS 归约、匿名性",
        "和量子安全均未形式化验证；不得表述为“论文安全证明已复现”。",
        "",
        "## 主张矩阵",
        "",
        "| 主张 | 状态 | 证据 | 限制 |",
        "| --- | --- | --- | --- |",
    ]
    for claim in claims:
        lines.append(
            f"| {claim['id']} | {claim['status']} | {claim['evidence']} | {claim['limitation']} |"
        )
    lines.extend(
        [
            "",
            "## 后端边界",
            "",
            "`constructed_relation` 使用 programmed H1，且",
            "`trapdoor_used=false`、`sample_pre_used=false`。它不能支持 malicious KGC、",
            "真实 ISIS trapdoor 或静态密钥分布主张。",
            "",
            "## 论文歧义和证明风险",
            "",
            "- `q=2^24-1` 被称为素数，但实际为合数；",
            "- correctness 使用 `n=5`，performance 使用 `n=6`；",
            "- `paper_performance` 不满足 `m>=2n*log2(q)`；",
            "- `tK` 被写成向量，但真实 GPV trapdoor 通常不是普通短向量；",
            "- `pk` 同时指 whole vector 与 `(u1,u2)`；",
            "- `s2` 被称为 partial private key，却经公开信道发送；",
            "- H2 同时承担 MAC、身份掩码和 KDF，论文未给域分离；",
            "- identity XOR 输出长度未定义；",
            "- `S` 中随机 `b` 的实现和传递口径不清；",
            "- Frodo 如何提供 TrapGen/SamplePre 未说明，官方实现未提供二者；",
            "- Definition 5 与 Lemma 3 在模回绕处存在可执行反例；",
            "- mBR matching-session 文字不自然，Game0-Game5 未机械化；",
            "- PFS、KCI、UKS、NKC 的非形式论证较简略。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("artifacts/processed/LCLA_AKA/security_audit.json"),
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        default=Path("reports/lcla_aka_security_audit.md"),
    )
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    evidence = audit(repo_root)
    json_output = args.json_output
    report_output = args.report_output
    if not json_output.is_absolute():
        json_output = repo_root / json_output
    if not report_output.is_absolute():
        report_output = repo_root / report_output
    json_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_output.write_text(render_report(evidence), encoding="utf-8")
    print(json.dumps({"result": evidence["result"], "claims": evidence["claim_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
