# LCLA-AKA 安全证明与主张审计

## 结论

状态机、静态代数关系和接受会话一致性可以执行检查，但无条件诚实执行
未达到 0.999 正确性标准，Definition 5/Lemma 3 还存在素数 q 模回绕反例。
身份未以明文字段出现在前两轮只属于结构检查。mBR、LWE/ISIS 归约、匿名性
和量子安全均未形式化验证；不得表述为“论文安全证明已复现”。

## 主张矩阵

| 主张 | 状态 | 证据 | 限制 |
| --- | --- | --- | --- |
| accepted_session_consistency | executable_checked | All accepted sessions explicitly check m1, m2, identity and session-key equality. | This is conditional on acceptance and does not establish honest-execution correctness. |
| honest_execution_correctness | empirically_not_reproduced | Continuous unscreened seeds are measured for every profile and both active distribution variants. | Observed acceptance rates are below the frozen 0.999 criterion. |
| lemma3_correctness | counterexample_found | Exhaustive small-q search finds prime-q modular-wrap counterexamples satisfying the stated error bound. | The literal Definition 5 formula was not changed to hide the counterexample. |
| static_key_binding | algebraically_checked | Constructed backend independently checks u1, u2, A*s2 and A*(s1+s2)+2f. | The static-key distribution and GPV trapdoor path are not reproduced. |
| intended_recipient_non_target_filtering | executable_checked | Twenty-candidate unconditional trials record non-target false accepts and true rejects. | Low non-target false accept alone does not establish availability or anonymity. |
| intended_recipient_target_availability | empirically_not_reproduced | Unconditional target true accepts and false rejects are both recorded. | The observed target false-reject rate prevents claiming complete filtering success. |
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
