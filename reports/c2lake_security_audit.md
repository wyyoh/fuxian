# C2LAKE Security Claim Audit

## Summary

- result: pass
- paper_sha256: 27502f8185258222a465750c124d1702b5a0bd387d8618f8f159b62258802e41
- eck_formally_verified: false
- rom_reduction_verified: false
- isis_hardness_verified: false
- cbi_isis_hardness_verified: false

## Evidence Boundary

- correctness 可通过代码执行路径与代数恒等式检查。
- 消息篡改与重放只能作为攻击模拟测试。
- eCK、ROM、forking lemma 与安全归约未做形式化验证。
- 本审计不得解释为论文安全证明已复现成功。

## Claim Matrix

| claim_id | status | formally_verified |
| --- | --- | --- |
| correctness | executable_checked | False |
| mutual_authentication | executable_checked | False |
| session_key_agreement | executable_checked | False |
| replay_resistance | executable_checked | False |
| impersonation_resistance | paper_proof_only | False |
| man_in_the_middle_resistance | paper_proof_only | False |
| known_key_security | paper_proof_only | False |
| unknown_key_share_resistance | paper_proof_only | False |
| no_key_control | paper_proof_only | False |
| perfect_forward_secrecy | paper_proof_only | False |
| known_session_key_security | paper_proof_only | False |
| type_i_adversary_proof | not_formally_verified | False |
| type_ii_adversary_proof | not_formally_verified | False |
| isis_reduction | not_formally_verified | False |
| cbi_isis_reduction | not_formally_verified | False |

## Known Paper Issues

- matrix_dimension_conflict: 论文前置 M 维度/秩表述与协议中 d^T M、x^T M、M y 同时成立的需求冲突。
- q_prime_vs_m_squared: 论文声称 q 为素数，但 Table 7 使用 q=m²，其中多个 q 为合数。
- h2_h3_local_field_typos: H2/H3 列表中存在局部字段下标或字段名排版疑点，需要按 canonical transcript 固定实现。
- theorem_1_sk_label_typo: Theorem 1 最后一行存在 SK 标签笔误。
- short_vector_bound_unclear: 部分安全证明依赖的短向量采样界未完整给出，literal/audited 需分开。
- key_agreement_timing_boundary_unspecified: Table 7 的 Key_Agreement 计时边界未说明，复现实验需并列报告 initiator/responder/full_handshake。

## Explicit Machine Flags

```json
{
  "cbi_isis_hardness_verified": false,
  "correctness_executable_checked": true,
  "eck_formally_verified": false,
  "forking_lemma_formally_verified": false,
  "isis_hardness_verified": false,
  "paper_security_proof_reproduced": false,
  "rom_reduction_verified": false,
  "tamper_and_replay_are_attack_simulations": true
}
```
