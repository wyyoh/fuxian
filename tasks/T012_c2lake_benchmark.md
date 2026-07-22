# Task ID
T012

# Objective
复现 C2LAKE Table 7 和 Figure 4，并明确原论文 Key_Agreement 计时口径不明。

# In scope
- 论文全部 m 参数
- literal q=m² 与 audited next-prime
- Setup/SetSecretValue/PartialExtract
- initiator、responder、full_handshake 三类协商时间
- warmup/repetitions
- CSV、统计表、图与报告

# Required settings
- 默认 warmup=10，repetitions=100。
- 记录 BLAS/线程环境。
- 首轮使用单线程环境变量。
- 大参数若内存不足不得悄悄降维，必须记录失败。

# Acceptance criteria
- 每个成功参数点有 raw CSV。
- 图由 CSV 自动生成。
- 报告列出论文值、复现均值、中位数、相对误差。
- literal 与 audited 单独绘图/表格。
- 解释硬件、Python/NumPy、矩阵生成和计时边界差异。
