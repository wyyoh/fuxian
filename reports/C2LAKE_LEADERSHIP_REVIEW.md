# 第一篇论文 C2LAKE 复现工作领导审阅报告

生成时间：2026-07-24 19:18 PDT  
复现对象：Provably secure lightweight certificateless lattice-based authenticated key exchange scheme for IIoT  
DOI：10.1002/cpe.7983  
交付分支：`exp/C2LAKE-full-reproduction`  
最终提交：`bc1144dbdc69d9c3060df253fd18c05038053cc7`

## 一页结论

第一篇 C2LAKE 论文的工程复现已经形成完整交付物：协议核心、完整握手流程、正确性测试、负向攻击模拟、理论成本复算、Table 7 / Figure 4 性能复现实验管线、最终报告和 CI evidence 均已完成。

本次交付可以作为“算法流程和可执行正确性复现”的审阅材料，但不能表述为“论文形式安全证明已由代码验证”。当前 machine result 为：

`pass_with_partial_benchmark_and_unverified_formal_security`

管理层可按以下口径审阅：

- 可执行复现：通过。
- 协议正确性：通过，包括双向认证验证式、K1/K2/K3 一致性、会话密钥一致性、消息篡改拒绝。
- 性能复现：部分完成。`m=32` 至 `m=160` 参数完成 exact benchmark；`m=256` 在当前环境超时，已保留失败记录。
- 安全证明：未形式化验证。eCK、ROM、ISIS/CBi-ISIS 归约仍属于论文证明范围，不由本代码证明。
- 生产可用性：当前是可审计 Python reference implementation，不是生产级密码学库。

## 工程交付状态

| 项目 | 状态 | 说明 |
| --- | --- | --- |
| 代码分支 | 已完成 | `origin/exp/C2LAKE-full-reproduction` |
| 最终 HEAD | 已确认 | `bc1144dbdc69d9c3060df253fd18c05038053cc7` |
| GitHub Actions | 成功 | run id `30138924254`，conclusion `success` |
| CI artifact | 存在 | `C2LAKE-full-evidence`，artifact id `8613801810` |
| 本地测试 | 通过 | `pytest` 为 `99 passed` |
| 主线合并 | 未完成 | `origin/main` 当前仍为 `2764e6353b8b710df71734990062d965fe500d09`，尚未包含 C2LAKE 最终工作 |
| PR 创建 | 阻塞 | 既有记录为 GitHub REST `401 Requires authentication`，未伪造 PR |

## 已复现内容

### 1. C2LAKE 协议核心

已实现：

- Setup；
- SetSecretValue；
- PartialPrivateKeyExtract；
- VerifyAndAssembleKey；
- Alice/Bob 完整握手流程；
- H1/H2/H3 类型化接口；
- paper literal 标量会话密钥；
- audited profile 的 32-byte SHAKE256 KDF；
- 时间戳策略；
- safe / fast 模运算 backend；
- deterministic reproduction RNG；
- uniform sampler 与 bounded ternary sampler。

实现遵守冻结口径：

- `M` 固定为 `n×n`；
- 内部向量统一为 shape `(n,)`；
- 所有运算后立即 `mod q`；
- `P=d^T M mod q`；
- 认证验证式和 K1/K2/K3 计算均有独立测试覆盖。

### 2. 协议正确性与负向测试

已验证：

- toy profile：1000 个独立完整会话通过；
- `paper_literal_m32`：100 个完整会话通过；
- `audited_prime_m32`：100 个完整会话通过；
- 双向认证均成功；
- K1、K2、K3 双方一致；
- 会话密钥双方一致；
- ephemeral secret `x/y/z` 未进入公开 transcript；
- request/response 字段篡改会被拒绝；
- timestamp 正常、过期、未来偏移边界均覆盖；
- q/profile/backend/identity/key 混用等上下文错误均覆盖。

### 3. 理论成本复算

已生成通信成本、存储成本和运算计数模型。报告中特别区分：

- `paper_compact_message_bytes`：按论文紧凑口径估算；
- `canonical_hash_encoding_bytes`：当前 SHAKE 输入编码长度；
- `network_wire_encoding_defined=false`：当前未实现专用网络 wire serializer。

因此，当前 hash 编码长度不能直接解释为网络通信开销，也不能直接用于否定或验证论文通信效率主张。

### 4. Table 7 / Figure 4 性能复现

已完成参数：

- `paper_literal_m32`、`m48`、`m64`、`m80`、`m96`、`m112`、`m128`、`m160`；
- `audited_prime_m32`、`m48`、`m64`、`m80`、`m96`、`m112`、`m128`、`m160`。

未完成参数：

- `paper_literal_m256`：profile-level timeout；
- `audited_prime_m256`：profile-level timeout。

benchmark 数据口径：

- actual measured success rows：14400；
- actual measured failure rows：0；
- placeholder rows：1800；
- profile-level timeouts：2；
- timeout 行明确标记为 `profile_timeout_placeholder`，不是 1800 次真实执行失败。

性能结论边界：

- `algorithmic_workflow_reproduced=true`；
- `reference_implementation_benchmark_completed=partial`；
- `strict_original_implementation_timing_reproduced=false`；
- `m256_completed=false`。

本实现是 `auditable_python_reference_implementation`，包含 dataclass 校验、数组复制/只读转换、shape/dtype/domain 校验、SHAKE256 编码、transcript hash、可选 audited KDF 以及 Python 对象/函数开销。绝对耗时偏差不能简单归因为硬件差异。

## 安全主张边界

本项目验证的是“可执行性质”，不是形式安全证明。

| 主张 | 当前证据级别 |
| --- | --- |
| correctness | 可执行检查 |
| mutual authentication 验证式 | 可执行检查 |
| session key agreement 一致性 | 可执行检查 |
| timestamp freshness | 可执行检查 |
| expired replay rejection | 可执行检查 |
| general replay resistance | 论文证明范围 |
| in-window replay prevention | 当前为 false，无 replay cache |
| eCK security | 未形式化验证 |
| ROM / forking lemma 归约 | 未形式化验证 |
| ISIS / CBi-ISIS 困难性 | 未由代码验证 |
| 其他对比方案性能 | 仅论文参考值，未运行复现 |

需要特别说明：当前实现没有 replay cache。同一合法 request 在有效时间窗口内重复提交，当前无状态 responder 会再次接受。因此本项目只能说明“时间戳可限制陈旧消息”，不能说明“完整重放防护已实现”。若要工程上防止窗口内重放，需要新增 nonce/session-id cache 或状态化去重机制。

## 主要论文歧义和处理方式

| 论文问题 | 处理方式 |
| --- | --- |
| `q` 被要求为素数，但 Table 7 使用 `q=m²`，通常为合数 | 分为 `paper_literal` 与 `audited_prime` 两套 profile |
| `M` 的维度/秩表述与协议公式冲突 | 冻结为 `n×n`，不声称满足论文 `rank m` |
| H2/H3 字段列表存在局部下标或字段名疑点 | 使用固定 canonical transcript，并在报告记录差异 |
| Theorem 1 最后一行 SK 标签疑似笔误 | 记录为论文排版/证明歧义 |
| 短向量采样界不完全明确 | literal/audited 分开处理，不隐藏冲突 |
| Table 7 `Key_Aggrement` 计时边界未说明 | 同时报告 `initiator_total`、`responder_total`、`full_handshake` |

## 交付物清单

领导审阅可重点查看以下文件：

- `reports/C2LAKE_FULL_REPRODUCTION.md`：完整技术复现报告；
- `reports/c2lake_full_validation.md`：统一验证摘要；
- `reports/c2lake_security_audit.md`：安全主张边界审计；
- `reports/c2lake_cost_reproduction.md`：通信、存储和运算成本复算；
- `reports/c2lake_benchmark_report.md`：Table 7 / Figure 4 性能复现报告；
- `artifacts/processed/C2LAKE/full_validation.json`：机器可读最终验证；
- `artifacts/processed/C2LAKE/final_claims_matrix.csv`：主张矩阵；
- `artifacts/raw/C2LAKE/benchmark_raw.csv`：经批准提交的 exact benchmark 原始数据；
- `artifacts/figures/C2LAKE/figure4_reproduced.png`：由 CSV 生成的 Figure 4 复现图。

论文 PDF 未提交到 Git，仅本地放置在 `papers/private/` 并由 `.gitignore` 忽略。提交的 manifest 只包含题名、DOI、SHA-256、页数和相关页码。

## 当前风险

1. 分支尚未合并到 `main`。如果领导审阅要求以主线为准，需要先完成 PR 或手工合并。
2. GitHub REST 创建 PR 曾因认证返回 401；需要补齐 GitHub 写权限或由仓库管理员创建 PR。
3. `m=256` exact benchmark 未完成；现有报告是“部分性能复现”，不是全参数性能复现。
4. 当前实现是 Python reference，不是生产级优化实现，也不是 C/硬件环境下的论文原始计时复现。
5. 形式安全证明未验证；不能对外宣称 eCK/ROM/ISIS/CBi-ISIS 已由代码证明。
6. 有效窗口内 replay prevention 未实现；如需工程落地，需要增加状态化 replay cache。

## 建议决策

建议将该交付物认定为：

“C2LAKE 论文算法流程、协议正确性、负向攻击模拟、理论成本与部分性能实验的可审计复现已完成。”

不建议将其表述为：

- “论文安全性已被代码证明”；
- “eCK 证明已验证”；
- “严格复现了论文原始实现性能”；
- “已形成生产级密码学实现”。

下一步建议：

1. 由仓库负责人将 `exp/C2LAKE-full-reproduction` 合并到 `main`，或授权创建 PR。
2. 如需补齐性能部分，在独立受控机器上续跑 `m=256` exact benchmark。
3. 如需面向产品落地，单独立项实现网络 wire serializer、replay cache、生产级随机源和常量时间/侧信道审计。
4. 如需支撑安全性对外声明，单独开展形式化证明审计或第三方密码学评审。
