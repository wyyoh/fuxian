# LCLA-AKA 算法复现报告

## 1. 论文与范围

复现对象为 *Quantum-Safe Lattice-Based Certificateless Anonymous Authenticated Key
Agreement for Internet of Things*，IEEE Internet of Things Journal 11(5)，
printed pages 9213–9225，DOI `10.1109/JIOT.2023.3323275`。

本报告只说明可执行算法和证据边界，不修改已经审查通过的 C2LAKE 数学实现。
论文 PDF 仅保存在 `papers/private/`，由 Git ignore 保护；仓库只提交 manifest。

## 2. 参数与不变量

保留五个冻结 profile：

| profile | m | n | q | family | 说明 |
| --- | ---: | ---: | ---: | --- | --- |
| toy | 32 | 2 | 127 | toy | 性质测试 |
| paper_correctness | 256 | 5 | 16777215 | paper_literal | 正确性段落 |
| paper_performance | 256 | 6 | 16777215 | paper_literal | 性能段落 |
| audited_preserve_keylen | 256 | 5 | 16777259 | audited | 保留 key length |
| audited_preserve_dimension | 288 | 6 | 16777259 | audited | 保留 n=6 并修正关系 |

`16777215=2^24-1` 是合数，只在 paper profile 中作为 expected warning；
`16777259` 通过素数检查。`paper_performance` 不满足
`m>=2*n*log2(q)`，audited profile 违反该关系会成为 unexpected error。

固定维度为：

- `A: n×m`，`s1/s2/s: m`，`f/pk_full/u1/u2: n`；
- `X_A/X_B: n×m`，`E_A/E_B/C_A/C_B: m×m`；
- `e_A/e_B/n_A/n_A'/n_B/n_B': m`；
- `delta_A/delta_B/m1/m2: m bits`。

所有 dataclass 均为 frozen/slots；数组构造时复制、设为只读并检查 shape、dtype、
Zq/bit domain。`pk_full` 与 `(u1,u2)` 使用不同字段，不再混名。

## 3. 数学后端

`safe` 在 int64 最坏累加不安全时回退 Python int；`fast` 在同一条件下稳定返回
`BACKEND_OVERFLOW_UNSAFE`。实现了矩阵乘、矩阵向量乘、转置方向乘法、加减、
标量乘、centered representative 和 bit pack/unpack。非对称小矩阵已知答案测试
避免只用左右实现互证。

离散高斯 reference sampler 的整数权重正比于
`exp(-pi*k^2/beta^2)`，使用显式尾截断和 PCG64 seed。PCG64 只用于可重复实验，
不被描述为生产级 CSPRNG。

## 4. Reconciliation

Definition 5 按原文实现 `mu_0`、`mu_1`、随机 bit 的 signal `S` 和：

`Mod2(x,delta)=((x+delta*((q-1)//2)) mod q) mod 2`。

边界穷举发现 literal Definition 5 与 Lemma 3 在模回绕处存在反例。例如
`q=127,b=0,e=-1,a=125` 时满足论文误差界，但两端 Mod2 不一致。这一冲突编号
`LCLA-D11`，没有通过改区间、减噪或固定 bit 隐藏。

## 5. 静态密钥后端

官方 FrodoKEM 源码 serial build 成功，但没有 LCLA 所需的 arbitrary `(n,m,q)`、
TrapGen、SamplePre、Definition 5 S/Mod2。因此：

- `real_trapdoor_backend.status=unavailable`；
- `toy_trapdoor_backend.status=not_implemented`；
- 可执行路径是 `constructed_relation`。

constructed 路径先采样 `s1,s2,f`，再构造并注册：

`pk_full=A(s1+s2)+2f mod q`，
`u1=As1+2f`，`u2=pk_full-u1`。

运行时检查 `As2=u2` 和 `A(s1+s2)+2f=pk_full`。每个结果明确携带
`programmed_h1=true`、`trapdoor_used=false`、`sample_pre_used=false`。
这一路径只复现代数关系，不能支持真实静态密钥分布、malicious KGC 或 ISIS
trapdoor 安全主张。

## 6. 哈希、身份与三轮状态机

实现采用 SHAKE256、长度前缀、类型/shape/q/profile 编码，并分域：

- `LCLA-MAC-A-v1`；
- `LCLA-MAC-B-v1`；
- `LCLA-ID-MASK-v1`；
- `LCLA-SESSION-KDF-v1`。

identity 必须是非空 UTF-8 string 或 bytes；Unicode 可完整恢复。mask 长度精确等于
identity 字节数，不假设 identity 恰好 m bits。canonical hash encoding 不等于网络
wire encoding；项目没有专用 wire serializer。

公开状态机严格是三轮：

1. Alice：`(C_A,delta_A,h_A)`；
2. Bob：`(C_B,h_B)`；
3. Alice：`(T_A,delta_B)`。

这三个 packet 包含论文统计的七个字段。第一、二轮没有明文 `ID_A/ID_B`，
第三轮 `T_A` 是等长 XOR mask；`X/E/e/m1/m2/static secret` 均不在 packet 中。

## 7. 可执行结果

固定 seed 矩阵共执行 1400 次：

| profile | 尝试 | 接受 | NOT_INTENDED_RECEIVER | RECONCILIATION_FAILURE |
| --- | ---: | ---: | ---: | ---: |
| toy | 1000 | 7 | 922 | 71 |
| paper_correctness | 100 | 40 | 31 | 29 |
| paper_performance | 100 | 77 | 12 | 11 |
| audited_preserve_keylen | 100 | 40 | 31 | 29 |
| audited_preserve_dimension | 100 | 79 | 16 | 5 |
| 合计 | 1400 | 243 | 1012 | 145 |

所有 243 个接受会话均满足：

- h_A、h_B 验证成功；
- `m1=m1'`、`m2=m2'`；
- paper m-bit session key 一致；
- audited 32-byte key 一致；
- Bob 恢复的 `ID_A` 与 Unicode 原文完全一致；
- transcript hash 一致。

因此“接受会话的代数一致性”已复现；“论文参数下每次都能成功协商”没有成立。
高拒绝率是 literal reconciliation 的观察结果，不能删除或归类为安全证明。

## 8. 负向、接收者与匿名结构

测试逐项篡改 `C_A/delta_A/h_A/C_B/h_B/T_A/delta_B`，以及
`A/s1/s2/f/u1/u2/pk_full/ID_A/ID_B`。篡改在接收者过滤、MAC、身份恢复、
static relation 或最终 pair validation 处被拒绝。

20 个候选 Bob、100 轮 intended-recipient 实验中，目标 Bob 在可协调 seed 上通过，
19 个非目标 Bob 不产生 response；意外通过为 0。它只支持 intended-recipient
filtering，不是匿名性证明。

第一、二轮没有明文 identity、第三轮 identity 被 mask 属于结构检查。
被动 transcript 匿名性、不可链接性和主动匿名游戏均未形式化验证。

## 9. 结论边界

已复现：代数关系、literal reconciliation 实现及反例、constructed static relation、
三轮流程、目标接收者过滤、接受会话 m1/m2/key/identity 一致、篡改拒绝与结构性
明文身份隐藏。

条件性/未复现：真实 TrapGen/SamplePre、Frodo native LCLA operation、真实静态密钥
分布、严格原始计时。

未验证：mBR Game0–Game5、LWE/ISIS 困难性、完整匿名性、malicious KGC 形式安全、
PFS/KCI/UKS/NKC 形式证明和量子安全证明。
