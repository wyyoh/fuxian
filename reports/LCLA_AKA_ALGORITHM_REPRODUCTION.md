# LCLA-AKA 算法重构与正确性失败分析

## 范围

本报告描述 LCLA-AKA 的可执行算法、分布口径和正确性边界。论文 PDF 只保存在
`papers/private/`，仓库仅提交 manifest。C2LAKE 数学实现未被修改。

## 固定维度与状态机

- A: n×m；
- s1/s2/s: m；
- f/pk_full/u1/u2: n；
- X_A/X_B: n×m；
- E_A/E_B/C_A/C_B: m×m；
- e_A/e_B/n_A/n_A'/n_B/n_B': m；
- delta_A/delta_B/m1/m2: m bits。

三轮 packet 为：

1. `AliceRequest(C_A,delta_A,h_A)`；
2. `BobResponse(C_B,h_B)`；
3. `AliceFinish(T_A,delta_B)`。

即 3 个网络 packet、7 个论文统计字段，不是 7 个独立网络 round。

## Distribution variants

`paper_literal_distribution`：

- s1 uniform over Zq^m；
- f/s2 权重 `exp(-pi*k²/(2*beta²))`；
- constructed backend 仍为 programmed H1，无 TrapGen/SamplePre。

`proof_consistent_small_secret`：

- s1/f/s2 均为 standard lattice Gaussian/small secret；
- 权重 `exp(-pi*k²/beta²)`。

`legacy_reference` 只解释旧数据，不能称为 paper literal。

## Static relation

constructed backend 检查：

`u1=A*s1+2f`，`u2=pk_full-u1`，
`A*s2=u2`，`A(s1+s2)+2f=pk_full`。

这些等式已通过独立 Python-int oracle。它们不等于真实 TrapGen/SamplePre，也不支持
malicious KGC 或 ISIS trapdoor 安全主张。

## Definition 5 / Lemma 3

literal 实现保留：

`Mod2(x,delta)=((x+delta*((q-1)//2)) mod q) mod 2`。

小奇数 q 穷举在素数 q=31 和 q=127 找到满足论文误差界的模回绕反例。
因此 `lemma3_universal_correctness=false`，没有通过改 μ、Mod2、beta 或噪声分布
消除失败。

## 无条件 correctness

5 个 profile × 2 个 active variant，每组 1000 个连续、预先固定且不替换的 seed：

| profile | paper literal accepted | proof-consistent accepted |
| --- | ---: | ---: |
| toy | 0/1000 | 0/1000 |
| paper_correctness | 0/1000 | 476/1000 |
| paper_performance | 0/1000 | 779/1000 |
| audited_preserve_keylen | 0/1000 | 477/1000 |
| audited_preserve_dimension | 0/1000 | 766/1000 |

合计 2,498/10,000，接受率 0.2498。冻结标准为 0.999，故：

- accepted session consistency：true；
- honest execution correctness reproduced：false；
- paper correctness claim reproduced：false。

accepted session consistency 仅表示已接受会话的 m1、m2、identity 与 session key
相同，不能用它替代无条件正确性。

## Intended-recipient

每个 variant 使用 1000 个无筛选 request，目标 Bob 与 19 个非目标 Bob 均处理：

- paper literal：目标 0/1000，非目标误接受 0/19000；
- proof-consistent：目标 876/1000，非目标误接受 0/19000。

该结果支持 implemented non-target filtering，但目标误拒绝必须同时报告；它也不是匿名性
形式证明。

## 证据边界

已实现：状态机、constructed relation、accepted session 一致性、失败分布测量、
identity mask/recovery、篡改拒绝。

未复现：真实 TrapGen/SamplePre、论文 literal static-key distribution 的真实生成、
高概率正确性、Lemma 3 universal correctness 和 strict Frodo timing。

未验证：mBR、LWE/ISIS、完整匿名性、malicious KGC、PFS/KCI/UKS/NKC 与量子安全
形式证明。
