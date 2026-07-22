# Task ID
T020

# Objective
调查并验证论文所称 Frodo LatticeCrypto Library 对当前复现所需接口的真实支持情况，只做探测，不实现完整协议。

# In scope
- 确定库来源、版本、构建系统和许可证
- 在隔离目录尝试构建
- 搜索/验证以下能力：
  - 矩阵运算
  - 离散高斯采样
  - reconciliation
  - TrapGen
  - SamplePre
  - 自定义 n,m,q
- 输出 capability matrix
- 给出 backend 建议

# Out of scope
- 自行伪造“库支持”
- 完整 LCLA-AKA
- 论文性能复现

# Acceptance criteria
- 每项能力标记：native / adaptable / absent / unknown。
- 给出构建日志和 commit/version。
- 若 TrapGen/SamplePre 缺失，明确建议 real trapdoor 替代库或 constructed backend。
- 不因库失败阻塞后续 toy/constructed 路线。
