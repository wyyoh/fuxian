# Task ID
T010

# Objective
实现 C2LAKE 公共模运算、Setup、用户秘密值、部分私钥提取与验证。

# Authoritative specifications
- DECISIONS D101–D106
- specs/c2lake/algorithm_spec.md
- specs/c2lake/shape_table.csv

# In scope
- modular vector/matrix helpers
- safe/fast matmul backend
- bounded/uniform vector samplers
- H1/H2/H3 接口骨架
- Setup
- SetSecretValue
- PartialPrivateKeyExtract
- VerifyAndAssembleKey

# Out of scope
- 密钥协商消息
- benchmark Table 7
- 安全 game 模拟

# Acceptance criteria
1. toy、paper_literal_m32、audited_prime_m32 均可运行。
2. 100 个 seed 下部分私钥验证全部通过。
3. 篡改 d_i0、P_i0、P_i1、ID 任一字段均应失败。
4. 所有 shape/range 检查有效。
5. safe 与 fast backend 在小参数下结果一致。
6. 测试不得通过硬编码 hash 输出。

# Required evidence
- 每个 profile 的样例 metadata
- 100-seed 测试摘要
- diff 与测试输出
