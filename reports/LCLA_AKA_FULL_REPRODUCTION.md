# LCLA-AKA Algorithm Reproduction and Partial Performance Replication

## 1. 执行摘要

本项目完成了 LCLA-AKA 的可审计 Python reference 实现、constructed 静态关系、
三轮状态机、负向测试、成本模型、Table IV/V reference benchmark 管线和
Figure 4–6 重绘。最终机器状态使用
`pass_with_partial_backend_and_partial_performance_unverified_formal_security`，
不使用可能暗示全部论文结论成立的简单 `pass`。

核心结论有三点：

1. 所有被协议接受的会话都具有一致的 `m1/m2/session key/identity`；
2. literal Definition 5/Lemma 3 在模回绕处存在反例，1400 次尝试中仅 243 次接受；
3. 官方 FrodoKEM 可 serial build，但没有论文所需 TrapGen/SamplePre 或 LCLA API，
   因此真实静态密钥生成和严格原始性能没有复现。

## 2. 论文与 PDF manifest

- 题目：*Quantum-Safe Lattice-Based Certificateless Anonymous Authenticated Key
  Agreement for Internet of Things*；
- IEEE Internet of Things Journal 11(5)，1 March 2024；
- printed pages 9213–9225；
- DOI：`10.1109/JIOT.2023.3323275`；
- PDF SHA-256：
  `5412a2962dbbbc3314cbe513d70946c0e238ba60c5debd9dfae6b7f5411bebe3`；
- file pages：13；
- `local_file_tracked=false`、`ieee_republication_restricted=true`。

仓库没有 PDF、全文提取、论文截图或表格原图。

## 3. 实现范围与 backend 分层

实现了 modular/Gaussian/reconciliation/hash/static/protocol/cost/benchmark/plot
独立模块。所有数组有冻结 shape/domain，不允许无约束 dict 传递密钥或协议状态。

| backend | 状态 | 能力 | 不能支持的主张 |
| --- | --- | --- | --- |
| numpy safe/fast | available | 模运算、reference protocol | 原生 Frodo 等价 |
| constructed_relation | available | programmed H1 与静态代数关系 | TrapGen/SamplePre、malicious KGC |
| real_trapdoor | unavailable | 无 | 真实静态分布、ISIS trapdoor |
| frodo_native LCLA | unavailable | FrodoKEM serial build only | arbitrary params、S/Mod2、LCLA protocol |
| toy_trapdoor | not implemented | 无 | 不能外推到论文参数 |

## 4. 参数冲突

paper literal 与 audited profile 并存。机器检查确认：

- `16777215` 为合数，和论文“odd prime”表述冲突；
- correctness 用 `n=5`，performance 用 `n=6`；
- `paper_performance` 不满足 `m>=2*n*log2(q)`；
- audited 使用素数 `16777259`；
- `audited_preserve_dimension(m=288,n=6)` 满足近似关系。

paper 冲突是 expected warning，audited 冲突是 unexpected error。

## 5. Dependency probe 与 Frodo 能力

探测对象为 Microsoft `PQCrypto-LWEKE` 官方仓库 commit
`7a4e7219d06305e16aef734213001cd8fefbcc14`。GCC 13.3.0、GNU Make 4.3 下
`make -C FrodoKEM OPT_LEVEL=REFERENCE -j1` 成功；`-j2` 暴露 KAT archive
ordering race，不影响 serial build 结论。

FrodoKEM 有固定参数矩阵/采样/hash primitive，但不提供 arbitrary `(n,m,q)`、
TrapGen、SamplePre、论文 Definition 5 reconciliation 或完整 LCLA 接口。
所以 `paper_frodo_backend_identified=true`、`paper_frodo_backend_built=true`，
但 `strict_original_operation_timing_reproduced=false`。

## 6. 离散高斯与 reconciliation

reference Gaussian 使用 `exp(-pi*k²/beta²)` 离散权重、显式尾截断和 PCG64。
测试覆盖可复现性、对称性、经验均值、正负样本、shape 与 cutoff；统计测试不被描述为
密码学安全证明。

S/Mod2 按 Definition 5 literal 实现并在 q/4 临界点穷举。发现
`LCLA-D11` 模回绕反例，且 paper/audited profile 均出现实际协商拒绝。
没有降低 beta、删除噪声、关闭 reconciliation 或固定输出 bit。

## 7. Static key generation

constructed backend 生成 `A,s1,s2,f` 并注册
`H1(ID)=A(s1+s2)+2f`，检查：

- `u1=As1+2f`；
- `u2=pk_full-u1`；
- `As2=u2`；
- `A(s1+s2)+2f=pk_full`。

`s2` 按论文 literal 是公开 KGC share，不被错误描述为单独保密。真正保密的是 `s1`
与组合 `s`。programmed registry 绑定 identity，同一 identity 冲突注册被拒绝。

## 8. 三轮协议和七字段

网络状态机为：

1. `AliceRequest(C_A,delta_A,h_A)`；
2. `BobResponse(C_B,h_B)`；
3. `AliceFinish(T_A,delta_B)`。

因此 `network_rounds=3`、`network_packets=3`、`transmitted_fields=7`。
“7 messages”在本项目中按统计字段解释，不能写成七个网络 packet。

## 9. Identity masking 与 intended-recipient filtering

第一、二轮 packet 无 `ID_A/ID_B` 字段；第三轮 `T_A=ID_A XOR mask`。
mask 由独立 H2 域、精确 identity 字节长度导出，Unicode 可恢复。

Bob 先计算 `C_A*s_B`、Mod2 和 h_A；失败返回 `NOT_INTENDED_RECEIVER`，不生成
response、ephemeral state 或 key。20 候选、100 轮攻击模拟中非目标意外通过为 0。
这是接收者过滤证据，不是完整匿名证明。

## 10. 正确性、m1/m2 与 session key

1400 次固定 seed 尝试的真实结果：

| profile | attempts | accepted | intended-filter reject | final reconciliation reject |
| --- | ---: | ---: | ---: | ---: |
| toy | 1000 | 7 | 922 | 71 |
| paper_correctness | 100 | 40 | 31 | 29 |
| paper_performance | 100 | 77 | 12 | 11 |
| audited_preserve_keylen | 100 | 40 | 31 | 29 |
| audited_preserve_dimension | 100 | 79 | 16 | 5 |

243 个接受会话全部满足 h_A/h_B、m1、m2、paper session bits、audited 32-byte key、
identity recovery 与 transcript hash 一致。1012 个 first-stage reject 和 145 个
final-stage reject 均保留。结果支持接受会话正确性，不支持论文参数 universal success。

## 11. 篡改与独立 oracle

公开三轮七字段及静态 A/s1/s2/f/u1/u2/pk_full/identity 均有单字段篡改测试。
失败路径不输出 accepted key，并返回稳定 error code。

独立 Python-int oracle 不调用协议派生 helper，重算 u1/u2/static relation、
C_A/n_A/n_A'、C_B/n_B/n_B'；reconciliation 使用已经独立边界审计的 S/Mod2。

## 12. 安全主张证据边界

| 层级 | 内容 |
| --- | --- |
| executable/algebraic | 接受会话正确性、static relation、接收者过滤、篡改拒绝 |
| structural | 第一/二轮无明文 ID、第三轮 mask |
| paper proof only | known-key、no-key-control、KCI、UKS、PFS 等 |
| backend not reproduced | malicious KGC、ISIS trapdoor |
| not formally verified | Type I/II、mBR、LWE reduction、匿名性、量子安全 |

`mbr_formally_verified=false`、`lwe_reduction_verified=false`、
`isis_hardness_verified=false`、`anonymity_formally_verified=false`、
`quantum_security_verified=false`、`paper_security_proof_reproduced=false`。

## 13. 理论通信、存储和运算成本

paper compact bit 数按 `2*m²*bitlen(q)+4m+identity_bits` 推导；
paper 固定 identity 假设取 m bits。`canonical_hash_encoding_bytes` 只描述当前
SHAKE transcript 编码，`network_wire_encoding_defined=false`，不能把它作为实际网络
通信量或用来验证论文通信效率。

存储表分别报告数学理想 bit 与 NumPy int64 bytes。真实 trapdoor 结构不可用，
因此存储标 unavailable，不用普通向量伪造。运算表分 setup、static、Alice create、
Bob verify/reply、Alice finish、Bob finish 与 full handshake。

## 14. Table IV 与 Table V

Table IV 15 个 paper operation 已人工交叉核对 printed p9222。NumPy reference
mapping 明确列出 included/excluded overhead。当前 reference 相对论文实现多出：

- dataclass/shape/dtype/domain/overflow validation；
- array copy/read-only conversion；
- canonical hash encoding 与 SHAKE256；
- Python object/function overhead。

Table IV 三位小数逐项乘 Num_A/Num_B 得 `4.210/4.178 ms`，但论文 Table V 是
`4.255/4.233 ms`；两者并列。Verify 的重构公式和 actually measured phases 也分列，
不把 paper reported、reconstructed 和 measured 混成一个数字。

## 15. Figure 4

Figure 4 数据由 Table V 的 per-entity Sum 重构为 entity scaling curve。
论文 reference、NumPy reference 和 audited profile 分开；Frodo native 曲线不存在。
趋势统计使用跨 entity 序列的 Spearman/单调性，不在单点上使用 `trend_match`。
Spearman 只表示秩趋势，不表示绝对计时复现成功。

## 16. Figure 5

Figure 5 的 LCLA 3 rounds/7 fields 为论文文字值；LCLA bit 数由七字段推导。
其他方案 rounds/field 公式来自论文文字，bit 曲线由两实体 payload 与 broadcast
叙述重构。所有曲线标明 `paper_reported_reference` 或 `reconstructed_partial`。

## 17. Figure 6

论文只给 `entities=50` 时最高约 10000 rounds、5000 messages、`10^8` bits，
LCLA 约 400/400/`10^7` 的示例，没有曲面公式。提交图使用明确的
`paper_narrative_example_fitted` 公式，状态 `partial`。

这些拟合值和 Figure 5 的每发起者 3 rounds/7 fields 及字段级 bit 数冲突。
报告没有目测拟合成“严格复现”，而是把冲突作为未解决歧义。

## 18. 性能实现范围

`benchmark_class=auditable_python_reference_implementation`。
已完成 reference smoke 与可恢复 exact 管线；严格 Frodo 原始计时未复现。
绝对偏差不能只归因于 CPU/OS，还来自 API 语义、校验、编码、SHAKE、数组表示与
Python overhead。

## 19. 论文歧义

已记录：

1. q 素数/合数冲突；
2. correctness n=5 与 performance n=6；
3. `paper_performance` 参数关系冲突；
4. tK trapdoor 类型表述；
5. pk whole vector/public components 混名；
6. s2 名称与公开传输；
7. H2 多用途无域分离；
8. identity XOR 长度未定义；
9. S 的随机 b 口径；
10. Frodo TrapGen/SamplePre 来源缺失；
11. Definition 5/Lemma 3 模回绕反例；
12. mBR matching-session/Game 文字；
13. PFS/KCI/UKS/NKC 论证简略；
14. Table IV 加权和与 Table V 不一致；
15. Figure 6 示例与 Figure 5 公式不一致。

## 20. 已复现、条件性与未验证

已复现：协议代数关系、literal reconciliation 行为、constructed static relation、
三轮消息流程、接收者过滤、接受会话 m1/m2/key/identity、结构性明文身份隐藏、
理论成本、reference benchmark 管线与重绘图。

条件性：real TrapGen/SamplePre、Frodo native、strict Table IV timing、真实静态分布。

未验证：mBR、LWE/ISIS 困难性、完整匿名性、量子安全、malicious KGC、
PFS/KCI/UKS/NKC 形式证明和其他方案的实际性能。

## 21. 后续建议

优先事项是从作者获取确切 Definition 5/S 实现、Frodo fork/commit、TrapGen/SamplePre
接口与 Figure 6 公式。若目标转向生产实现，应使用 CSPRNG、固定 wire serializer、
侧信道审计、真实 trapdoor 库和独立密码分析；当前 reference 代码不能直接部署。
