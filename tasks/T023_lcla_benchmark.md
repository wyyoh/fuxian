# Task ID
T023

# Objective
复现 LCLA-AKA Table IV/V 与 Figure 4–6，分离公式通信成本、协议层性能和真实 trapdoor 性能。

# In scope
- paper_correctness
- paper_performance
- audited profiles
- basic operation benchmark
- protocol benchmark
- communication rounds/messages/bits
- single/multiple initiator figures

# Acceptance criteria
- raw CSV + metadata。
- Table IV 操作名与论文映射清晰。
- Table V 同时标注 backend。
- Figure 5/6 提供论文公式复画和实现字段实算两套曲线。
- 若 real trapdoor 不可用，静态密钥生成结果标注 not reproduced；不得用 constructed 值冒充。
