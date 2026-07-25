# LCLA-AKA 安全证明与主张审计

## 结论

协议正确性、目标接收者过滤、MAC 篡改拒绝和接受会话密钥一致性可以执行检查。
身份未以明文字段出现在前两轮只属于结构检查。mBR、LWE/ISIS 归约、匿名性和
量子安全均未形式化验证；不得表述为“论文安全证明已复现”。

## 主张矩阵

| 主张 | 状态 | 证据 | 限制 |
| --- | --- | --- | --- |
| correctness | executable_checked | Accepted sessions check m1, m2, identity and key equality; literal reconciliation failures are retained. | Definition 5/Lemma 3 has an executable modular-wrap counterexample, so universal correctness is not established. |
| static_key_binding | algebraically_checked | Constructed backend independently checks u1, u2, A*s2 and A*(s1+s2)+2f. | The static-key distribution and GPV trapdoor path are not reproduced. |
| intended_recipient_filtering | executable_checked | Twenty-candidate attack simulation rejects non-target recipients before response generation. | This is filtering evidence, not a formal anonymity result. |
| mutual_authentication | executable_checked | h_A and h_B tamper simulations reject altered first/second-round packets. | Only the implemented model and constructed backend are checked. |
| session_key_agreement | executable_checked | All accepted sessions explicitly compare m1, m2 and both session-key outputs. | Some literal sessions reject because reconciliation disagrees. |
| identity_anonymity | structural_checked | Rounds 1 and 2 contain no identity fields; T_A masks Alice identity in round 3. | Passive-transcript anonymity and unlinkability are not formally verified. |
| public_key_replacement_resistance | paper_proof_only | The paper argues identity-to-pk binding. | No formal Type-I game is implemented. |
| malicious_KGC_resistance | backend_not_reproduced | Constructed backend uses programmed H1 and no TrapGen/SamplePre. | Constructed relations cannot support this claim. |
| known_key_security | paper_proof_only | Paper informal analysis only. | No formal game implemented. |
| no_key_control | paper_proof_only | Paper informal analysis only. | No formal game implemented. |
| KCI_resistance | paper_proof_only | Paper informal analysis only. | No formal game implemented. |
| UKS_resistance | paper_proof_only | Paper informal analysis only. | No formal game implemented. |
| perfect_forward_secrecy | paper_proof_only | Paper informal analysis only. | No compromise experiment implemented. |
| Type_I_adversary | not_formally_verified | Proof text audited. | Game and reduction are not mechanized. |
| Type_II_adversary | not_formally_verified | Proof text audited. | Game and reduction are not mechanized. |
| mBR_security | not_formally_verified | Game0-Game5 narrative audited. | Matching sessions, oracle programming and game hops are not formalized. |
| LWE_reduction | not_formally_verified | Reduction claim identified. | LWE hardness and reduction tightness are not verified by code. |
| ISIS_security | backend_not_reproduced | No real TrapGen/SamplePre backend is available. | Constructed preimages provide algebraic relations only. |
| quantum_security | not_formally_verified | Underlying assumptions are catalogued. | No quantum-security proof is reproduced. |

## 后端边界

`constructed_relation` 使用 programmed H1，且
`trapdoor_used=false`、`sample_pre_used=false`。它不能支持 malicious KGC、
真实 ISIS trapdoor 或静态密钥分布主张。

## 论文歧义和证明风险

- `q=2^24-1` 被称为素数，但实际为合数；
- correctness 使用 `n=5`，performance 使用 `n=6`；
- `paper_performance` 不满足 `m>=2n*log2(q)`；
- `tK` 被写成向量，但真实 GPV trapdoor 通常不是普通短向量；
- `pk` 同时指 whole vector 与 `(u1,u2)`；
- `s2` 被称为 partial private key，却经公开信道发送；
- H2 同时承担 MAC、身份掩码和 KDF，论文未给域分离；
- identity XOR 输出长度未定义；
- `S` 中随机 `b` 的实现和传递口径不清；
- Frodo 如何提供 TrapGen/SamplePre 未说明，官方实现未提供二者；
- Definition 5 与 Lemma 3 在模回绕处存在可执行反例；
- mBR matching-session 文字不自然，Game0-Game5 未机械化；
- PFS、KCI、UKS、NKC 的非形式论证较简略。
