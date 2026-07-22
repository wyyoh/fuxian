# Task ID
T011

# Objective
实现 C2LAKE 双向认证密钥协商和正确性/负向测试。

# In scope
- transcript dataclasses
- initiator create
- responder verify/reply
- initiator verify/finish
- canonical K1/K2/K3
- timestamp policy
- session key derivation
- protocol tests

# Out of scope
- eCK game
- ISIS/CBi-ISIS 求解器
- Table 7 benchmark

# Acceptance criteria
1. 1000 个 toy 会话双方 SK 相等。
2. 至少 100 个 m32 literal 和 audited 会话成功。
3. 显式断言 K1、K2、K3 双方逐项相等。
4. 篡改 ID、P0、P1、X、Y、Z、S、T 任一字段被拒绝。
5. 过期和未来超窗时间戳被拒绝。
6. 不同 transcript 顺序或编码不能产生相同 hash 输入。
7. 所有失败返回稳定错误码。

# Required evidence
- property test 摘要
- 一条完整 transcript 的去敏结构
- 失败案例矩阵
