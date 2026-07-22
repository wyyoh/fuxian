# Task ID
T022

# Objective
实现 LCLA-AKA 静态密钥接口和三轮匿名认证密钥协商。

# In scope
- static key generation via backend
- Alice request
- Bob response
- Alice finish
- Bob finish
- intended receiver filtering
- ID mask/recovery
- session KDF
- positive/negative/multi-entity tests

# Acceptance criteria
1. toy 与 constructed profile 下 m1、m2、SK 双方一致。
2. 1000 个 toy 会话成功。
3. 多接收者中仅目标 Bob 通过首轮 MAC。
4. 前两轮 transcript schema 不含明文 ID。
5. Bob 可精确恢复 UTF-8 IDA。
6. 篡改 C_A、delta_A、h_A、C_B、h_B、T_A、delta_B 均失败或密钥不接受。
7. constructed 结果报告不得标为 real trapdoor。
