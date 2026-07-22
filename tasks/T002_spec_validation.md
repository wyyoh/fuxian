# Task ID
T002

# Objective
将两篇论文的 shape table、parameter profiles 和 claims matrix 变成可机器校验的规格，不实现协议。

# In scope
- CSV/YAML schema validation
- profile 交叉检查
- 维度表达式解析
- 参数冲突告警
- 生成 `reports/spec_validation.md`

# Required checks
1. C2LAKE 每个 benchmark m 的 n 是否等于 ceil(4m log2m)。
2. 标记 paper q 是否为素数，不因非素数而拒绝 literal。
3. LCLA paper_performance 是否违反 m>=2n log2(q)，报告 warning。
4. audited q 必须为素数。
5. claims matrix 的 class 只能为 executable、empirical、formal/non-executable 或组合标记。
6. shape 表 symbol 不重复。
7. profile family 与 backend 合法。

# Acceptance criteria
- 生成机器可读 validation JSON。
- 所有已知冲突均作为 expected warning，而非静默。
- 无 unexpected error。
