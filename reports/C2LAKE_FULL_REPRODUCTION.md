# C2LAKE Full Reproduction Report

## 1. 论文基本信息

- title: Provably secure lightweight certificateless lattice-based authenticated key exchange scheme for IIoT
- DOI: 10.1002/cpe.7983
- 本地 PDF 不提交；仅提交 `papers/C2LAKE_MANIFEST.yaml` 中的 SHA-256、页数和相关页码。

## 2. 实现范围

已实现 C2LAKE 的 Setup、SetSecretValue、PartialPrivateKeyExtract、VerifyAndAssembleKey、Alice/Bob 完整协议握手、H1/H2/H3 编码接口、literal scalar 会话密钥、audited 32-byte KDF、时间戳策略、负向测试、成本模型和 benchmark 管线。

未实现第二篇 LCLA-AKA；未实现 eCK game、ROM 形式证明、ISIS/CBi-ISIS 求解器或安全归约验证。

## 3. literal/audited 参数

- `paper_literal_m*`: 使用论文 Table 7 的 `q=m²`，即使 q 通常为合数；该冲突作为 expected warning/复现歧义记录。
- `audited_prime_m*`: 使用 `next_prime(m²)`，且要求 `q_must_be_prime=true`。
- `toy`: 用于快速性质测试和 CI smoke。

## 4. 公式和代码映射

- `P=d^T M mod q`: `setup`
- `P_i1=d_i1^T M mod q`: `set_secret_value`
- `P_i0=r_i^T M mod q`: `extract_partial_private_key`
- `d_i0=r_i+h1_i*d mod q`: `extract_partial_private_key`
- `S_i=x_i+h2_i(d_i0+d_i1) mod q`: `initiator_create_request`
- `S_i^T M == X_i+h2_i(P_i0+P_i1+h1_iP)`: `verify_initiator_auth`
- `K1/K2/K3`: `derive_initiator_components` 与 `derive_responder_components`
- `H3(...)`: `derive_session_result`

## 5. 协议消息流程

请求公开字段：`ID_i, P_i0, P_i1, X_i, Y_i, Z_i, S_i, T_i`。

响应公开字段：`ID_j, P_j0, P_j1, X_j, Y_j, Z_j, S_j, T_j`。

本地 ephemeral secret `x,y,z` 保存在 frozen/slots dataclass 状态中，不进入公开 transcript。

## 6. 正确性结果

单元测试覆盖 toy 1000 个完整会话、`paper_literal_m32` 100 个完整会话、`audited_prime_m32` 100 个完整会话。统一验证脚本在 smoke 模式重新执行协议正确性检查。

## 7. 负向测试

请求与响应的 identity、公钥分量、X/Y/Z、S、timestamp 均有单字段篡改测试。预期错误码分别为 `INVALID_INITIATOR_AUTH` 或 `INVALID_RESPONDER_AUTH`。

## 8. K1/K2/K3 一致性

双方独立计算 K1、K2、K3，并在高层 `run_handshake` 中显式比较；不允许跳过验证或硬编码会话密钥。

## 9. 会话密钥一致性

`paper_literal` 输出 H3 标量；`audited_prime` 同时输出 32-byte SHAKE256 KDF。双方结果必须一致。

## 10. 时间戳和重放测试

时间单位统一为整数秒。测试覆盖正常时间、最大年龄边界、超过最大年龄、最大未来偏移边界、超过未来偏移、旧 request replay、旧 response replay。

## 11. 安全主张证据边界

代码只能验证可执行性质：正确性、消息篡改拒绝、重放窗口和会话一致性。eCK、ROM、forking lemma、ISIS/CBi-ISIS 归约未形式化验证。

## 12. 理论通信成本

成本模型分别报告论文忽略 ID/T 的口径与实现长度前缀序列化口径。所有 Zq 元素位长使用 `ceil(log2(q))`，避免混淆 `log m`、`log2 m`、`log²m`、`log³m`。

## 13. 理论存储成本

报告数学理想位长、当前 NumPy int64 实际内存，以及 benchmark 优化存储估计；不声称当前实现已做压缩存储优化。

## 14. 运算计数

成本模型按 Setup、SetSecretValue、PartialPrivateKeyExtract、initiator_create、responder_verify_and_reply、initiator_verify_and_finish、full_handshake 统计向量矩阵乘、矩阵向量乘、点积、向量加法、标量乘向量和 H1/H2/H3。

## 15. Table 7 结果

论文 Table 7 参考值保存于 `specs/c2lake/paper_table7_reference.csv`。复现实验输出 raw CSV、统计 CSV 和论文值比较 CSV。Key_Agreement 原论文计时边界不明，因此比较表同时列出 `initiator_total`、`responder_total` 和 `full_handshake`。

本地 exact 尝试完成了 `m=32,48,64,80,96,112,128,160` 的 `paper_literal` 与 `audited_prime` profile。`m=256` 的 `paper_literal_m256` 与 `audited_prime_m256` 在默认单 profile timeout 下未完成，raw CSV 中保留 `timeout` 失败行。

## 16. Figure 4

`scripts/reproduce_c2lake_figure4.py` 从 CSV 自动生成 `artifacts/figures/C2LAKE/figure4_reproduced.png`。图不手填数据。

## 17. 论文值与复现值偏差

偏差由 `artifacts/processed/C2LAKE/table7_comparison.csv` 计算，包含 `absolute_error_ms`、`relative_error_percent` 和 `trend_match`。硬件、Python/NumPy 版本、BLAS 与操作系统差异会影响绝对时间。

## 18. 硬件和软件环境

raw benchmark CSV 每行记录 Python、NumPy、CPU、OS、git commit、timestamp、backend 和 seed。CI 仅运行 smoke benchmark。

## 19. 论文歧义

- M 维度/秩表述与协议公式冲突；实现固定为 `n×n`。
- q 声称为素数，但 Table 7 使用 `q=m²`。
- H2/H3 字段列表存在局部下标或字段名排版疑点。
- Theorem 1 最后一行 SK 标签疑似笔误。
- 短向量采样界对部分向量未完全明确。
- Table 7 `Key_Aggrement` 计时边界未说明。

## 20. 无法复现的部分

未形式化复现 eCK 安全证明、ROM 安全归约、ISIS/CBi-ISIS 困难性或其他对比方案的实际运行性能。

性能实验方面，`m=256` 的 exact 参数在当前环境未完成；报告中标为 timeout，不用 toy 或较小参数替代。

## 21. 后续优化建议

- 对大参数引入可审计的分块矩阵乘，降低峰值内存。
- 增加可选压缩存储 backend，但必须继续保留 safe reference。
- 若需要安全证明复核，应单独建立形式化证明任务，而不是从测试结果推出安全结论。

## 结论

已复现：协议可执行性、部分私钥验证、双向认证验证式、K1/K2/K3 一致性、会话密钥一致性、消息篡改拒绝、时间戳和重放窗口、理论成本重算，以及已完成的性能实验。

未验证：eCK 形式安全、ROM 安全归约、ISIS/CBi-ISIS 困难性、Type I/II 证明的形式化正确性，以及论文其他对比方案的实际运行性能。
