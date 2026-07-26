# LCLA-AKA Algorithm Reconstruction, Conditional-Path Validation, and Correctness-Failure Analysis

## 1. 执行摘要

本项目重构了 LCLA-AKA 三轮状态机、constructed static relation、哈希与身份掩码、
Definition 5 reconciliation、成本模型、reference benchmark 和 Figure 4–6 的部分
数据重绘。最终机器状态为：

`partial_reproduction_observed_correctness_failure_constructed_backend_unverified_security`

这不是“协议完整正确复现”。精确无条件试验的核心结果是：

- 5 个 profile × 2 个 active distribution variant × 1000 个连续 seed；
- 10,000 次诚实执行仅接受 2,498 次，总接受率 0.2498；
- `paper_literal_distribution` 在所有 profile 均为 0/1000；
- proof-consistent 小秘密分布最高接受率为 0.779；
- 所有结果低于预先冻结的 0.999 正确性标准；
- 已接受会话内部的 m1/m2/session key 一致；
- Definition 5/Lemma 3 在素数 q=31、127 上存在满足误差界的模回绕反例。

因此：

- `accepted_session_consistency=true`；
- `honest_execution_correctness_reproduced=false`；
- `paper_correctness_claim_reproduced=false`；
- `lemma3_universal_correctness=false`。

## 2. 论文、PDF 与版权边界

- 论文：*Quantum-Safe Lattice-Based Certificateless Anonymous Authenticated Key
  Agreement for Internet of Things*；
- IEEE Internet of Things Journal 11(5)，1 March 2024；
- printed pages 9213–9225；
- DOI：`10.1109/JIOT.2023.3323275`；
- PDF SHA-256：
  `5412a2962dbbbc3314cbe513d70946c0e238ba60c5debd9dfae6b7f5411bebe3`；
- file pages：13；
- `local_file_tracked=false`；
- `ieee_republication_restricted=true`。

仓库未提交 PDF、全文提取、论文截图、表格原图或 Figure 2–6 复制图片。

## 3. 参数与论文冲突

保留 toy、paper_correctness、paper_performance、audited_preserve_keylen 和
audited_preserve_dimension 五个 profile。机器检查确认：

- paper q=`16777215=2^24-1` 为合数，与“odd prime”表述冲突；
- audited q=`16777259` 为素数；
- correctness 使用 n=5，performance 使用 n=6；
- paper_performance 不满足 `m>=2*n*log2(q)`；
- audited_preserve_dimension(m=288,n=6) 满足该近似关系。

paper 冲突保留为 expected warning，不用 audited 参数冒充论文 literal。

## 4. Execution distribution variants

### paper_literal_distribution

- s1：uniform over `Zq^m`；
- f：论文 Definition 3 字面权重
  `exp(-pi*k²/(2*beta²))`；
- s2：constructed backend 预选自同一 paper Gaussian；
- `programmed_h1=true`；
- `trapdoor_used=false`；
- `sample_pre_used=false`。

这一路径恢复了论文长期秘密和噪声的字面分布，但 constructed backend 仍不是真实
TrapGen/SamplePre。

### proof_consistent_small_secret

- s1、f、s2：standard lattice Gaussian/small secret；
- 权重 `exp(-pi*k²/beta²)`；
- 仍使用 programmed H1 与 constructed relation。

### legacy_reference

只用于解释修订前数据，不是 paper literal。旧 49,209 行 benchmark 以及旧 1,400
次协议统计均明确归入此类，不与两种 active variant 混合。

## 5. 后端边界

| backend | 状态 | 可执行内容 | 不能支持 |
| --- | --- | --- | --- |
| NumPy safe/fast | available | modular/reference protocol | 原生 Frodo 等价 |
| constructed_relation | available | programmed H1、静态代数关系 | TrapGen/SamplePre、malicious KGC |
| real_trapdoor | unavailable | 无 | 真实静态密钥分布 |
| Frodo native LCLA | unavailable | FrodoKEM serial build only | arbitrary 参数、S/Mod2、LCLA |
| toy trapdoor | not implemented | 无 | 不能外推到论文参数 |

官方 Microsoft PQCrypto-LWEKE/FrodoKEM serial build 成功，但未提供论文所需
TrapGen、SamplePre 或 LCLA API。real static key generation 未复现。

## 6. 状态机与代数关系

公开网络状态机严格为三轮：

1. `AliceRequest(C_A,delta_A,h_A)`；
2. `BobResponse(C_B,h_B)`；
3. `AliceFinish(T_A,delta_B)`。

即 `network_rounds=3`、`network_packets=3`、`transmitted_fields=7`。公开 packet
不含 X/E/e、m1/m2 或 static secret。

constructed static relation 独立检查：

- `u1=A*s1+2f`；
- `u2=pk_full-u1`；
- `A*s2=u2`；
- `A(s1+s2)+2f=pk_full`。

这证明 implemented relation 自洽，不证明真实 SamplePre 分布或 malicious KGC 安全。

## 7. 无条件 correctness matrix

所有 seed 在执行前固定且连续，失败后不替换 seed：

| profile | variant | attempts | accepted | rate | Wilson 95% | first-stage reject | final reject |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: |
| toy | paper literal | 1000 | 0 | 0.000 | [0.0000, 0.0038] | 1000 | 0 |
| toy | proof-consistent | 1000 | 0 | 0.000 | [0.0000, 0.0038] | 996 | 4 |
| paper_correctness | paper literal | 1000 | 0 | 0.000 | [0.0000, 0.0038] | 1000 | 0 |
| paper_correctness | proof-consistent | 1000 | 476 | 0.476 | [0.4452, 0.5070] | 328 | 196 |
| paper_performance | paper literal | 1000 | 0 | 0.000 | [0.0000, 0.0038] | 1000 | 0 |
| paper_performance | proof-consistent | 1000 | 779 | 0.779 | [0.7522, 0.8036] | 116 | 105 |
| audited keylen | paper literal | 1000 | 0 | 0.000 | [0.0000, 0.0038] | 1000 | 0 |
| audited keylen | proof-consistent | 1000 | 477 | 0.477 | [0.4462, 0.5080] | 294 | 229 |
| audited dimension | paper literal | 1000 | 0 | 0.000 | [0.0000, 0.0038] | 1000 | 0 |
| audited dimension | proof-consistent | 1000 | 766 | 0.766 | [0.7388, 0.7912] | 126 | 108 |

合计 first-stage false reject 6,860 次，final reconciliation failure 642 次，
unexpected other failure 0 次。已接受的 2,498 次会话均满足 m1、m2、session key
和 identity recovery 一致；该条件性事实不等于诚实执行高概率正确。

## 8. Definition 5 / Lemma 3 审计

未修改论文 literal μ 区间或 Mod2 公式。对 q=7、11、15、31、63、127 穷举：

| q | prime | qualifying errors | violating tuples | first counterexample |
| ---: | --- | ---: | ---: | --- |
| 7 | yes | 0 | 0 | 无 |
| 11 | yes | 1 | 0 | 无 |
| 15 | no | 1 | 0 | 无 |
| 31 | yes | 5 | 48 | base=0, e=-2, close=27, b=0 |
| 63 | no | 13 | 336 | base=0, e=-6, close=51, b=0 |
| 127 | yes | 29 | 1680 | base=0, e=-14, close=99, b=0 |

q=31、127 的首个反例均满足论文误差界并跨越模边界。因此
`paper_correctness_proof_supported=false`。项目没有通过改公式、降低噪声或固定 bit
消除反例。

## 9. Intended-recipient 无条件统计

paper_performance 下，每种 variant 使用 1000 个连续 Alice request；每个 request
由目标 Bob 和 19 个非目标 Bob 处理：

| variant | target true accept | target false reject | non-target false accept | non-target true reject |
| --- | ---: | ---: | ---: | ---: |
| paper literal | 0 | 1000 | 0 | 19000 |
| proof-consistent | 876 | 124 | 0 | 19000 |

非目标误接受率为 0 只支持 implemented non-target filtering。paper literal 目标误拒绝
率 1.0、proof-consistent 目标误拒绝率 0.124，不能声称 filtering “完全成功”，更不
构成匿名性证明。

## 10. 身份、篡改与结构匿名性

第一、二轮无明文 ID 字段；第三轮 `T_A=ID_A XOR mask`，Unicode identity 可恢复。
该结论是结构检查，不是被动 transcript 匿名性、不可链接性或主动匿名游戏证明。

逐项篡改 C_A/delta_A/h_A/C_B/h_B/T_A/delta_B 与静态 A/s1/s2/f/u1/u2/
pk_full/identity 均由 implemented checks 拒绝或在最终 pair validation 失败。

## 11. Benchmark 语义修订

旧 49,209 行 raw 数据保留为 `legacy_reference`。旧协议 phase 使用预先确认成功 seed，
正确名称是 `conditional_success_path_latency`；seed 搜索和失败时间未计入。

新 exact raw：

- 文件：`correctness_patch_benchmark_exact.csv`；
- 行数：13,021；
- SHA-256：
  `80caacbea5a350d538fb2519da5bfcd0836b7ef6ee161583372b6b8950f884e2`；
- actual measured success：6,272；
- actual measured failure：6,743；
- dependency placeholder：6；
- T_Samp0/1/2：每种 active variant 各 1000 次；
- unconditioned attempt：成功和失败全部保留；
- retry-until-success：逐次与 total-end-to-end 同时保留；
- `retry_time_included=true`。

当无条件 acceptance probability 为 0 时，不伪造有限 expected time per success。
conditional success path 不能直接与论文 Table V 严格等价。

## 12. 成本、Table IV/V 与 Figure 4–6

通信模型区分 paper compact bits、canonical hash encoding 与未定义的 network wire
encoding。canonical encoding 不能被当作网络通信量。

Table IV NumPy reference exact 完成，但不是 Frodo native。Table IV 三位小数加权
得到 Num_A/Num_B=4.210/4.178 ms，与论文 Table V 的 4.255/4.233 ms 不一致。
Table V legacy measured phases 是条件成功路径，不能据此复现端到端正确性或重试成本。

Figure 4 为 reconstructed；Figure 5 为 reconstructed；Figure 6 仅为
partial/example-fitted。其他方案只保留 `paper_reported_reference`，未运行其实现。

## 13. 安全主张边界

| 主张 | 状态 |
| --- | --- |
| accepted_session_consistency | executable_checked |
| honest_execution_correctness | empirically_not_reproduced |
| lemma3_correctness | counterexample_found |
| intended_recipient_non_target_filtering | executable_checked |
| intended_recipient_target_availability | empirically_not_reproduced |
| identity plaintext absence | structural_checked |
| malicious KGC / ISIS trapdoor | backend_not_reproduced |
| mBR、Type I/II、LWE、匿名性、量子安全 | not_formally_verified |

`anonymity_formally_verified=false`、`mbr_formally_verified=false`、
`lwe_reduction_verified=false`、`isis_hardness_verified=false`、
`quantum_security_verified=false`、`malicious_kgc_security_reproduced=false`。

## 14. 最终结论

已完成：

- 论文三轮状态机重构；
- constructed static relation；
- accepted session 一致性；
- 无筛选失败分布测量；
- reconciliation 反例审计；
- reference operation benchmark；
- 部分 Figure 4–6 重构。

未完成或未成立：

- real TrapGen/SamplePre；
- 论文 literal static-key distribution 的真实生成；
- overwhelming-probability correctness；
- Lemma 3 universal correctness；
- strict Frodo timing；
- 形式安全与匿名性证明。

当前代码是可审计研究 reference，不可直接用于生产部署。
