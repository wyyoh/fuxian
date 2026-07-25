# LCLA-AKA Table IV Reference Benchmark

## 证据边界

- 论文 Frodo 仓库已识别且 serial build 成功，但没有 LCLA 所需的任意参数、
  Definition 5 reconciliation、TrapGen 或 SamplePre API。
- 本表是 `numpy_reference` 映射；包含 shape/overflow 检查、Python 对象开销、
  canonical 编码和 SHAKE256 开销，不是论文 Frodo 原生操作的严格计时复现。
- `strict_original_operation_timing_reproduced=false`。
- unavailable dependency 使用 placeholder，`actual_execution_attempted=false`，
  不计作独立执行失败。

## 论文值与 reference 测量

| profile | operation | paper ms | mean ms | median ms | 相对误差 % |
| --- | --- | ---: | ---: | ---: | ---: |
| paper_performance | T_H1 | 0.002 | 0.015010 | 0.015010 | 650.52 |
| paper_performance | T_H2 | 0.005 | 20.950546 | 20.950546 | 418910.92 |
| paper_performance | T_Mod | 0.837 | 0.092086 | 0.092086 | 89.00 |
| paper_performance | T_Samp0 | 0.013 | 0.055183 | 0.055183 | 324.49 |
| paper_performance | T_Samp1 | 0.291 | 1.200569 | 1.200569 | 312.57 |
| paper_performance | T_Samp2 | 0.004 | 0.106245 | 0.106245 | 2556.14 |
| paper_performance | T_Sign | 0.014 | 0.826121 | 0.826121 | 5800.86 |
| paper_performance | T_add0 | 0.267 | 16.311090 | 16.311090 | 6009.02 |
| paper_performance | T_add1 | 0.001 | 0.078308 | 0.078308 | 7730.80 |
| paper_performance | T_mod0 | 0.173 | 0.526410 | 0.526410 | 204.28 |
| paper_performance | T_mod1 | 0.002 | 0.005439 | 0.005439 | 171.93 |
| paper_performance | T_mul0 | 1.313 | 0.877316 | 0.877316 | 33.18 |
| paper_performance | T_mul1 | 0.145 | 0.080218 | 0.080218 | 44.68 |
| paper_performance | T_mul2 | 0.004 | 0.034816 | 0.034816 | 770.40 |
| paper_performance | T_xor | 0.001 | 0.013081 | 0.013081 | 1208.15 |
| toy | T_H1 | 0.002 | 0.011228 | 0.011228 | 461.42 |
| toy | T_H2 | 0.005 | 0.382234 | 0.382234 | 7544.68 |
| toy | T_Mod | 0.837 | 0.029917 | 0.029917 | 96.43 |
| toy | T_Samp0 | 0.013 | 0.040293 | 0.040293 | 209.95 |
| toy | T_Samp1 | 0.291 | 0.094035 | 0.094035 | 67.69 |
| toy | T_Samp2 | 0.004 | 0.075589 | 0.075589 | 1789.71 |
| toy | T_Sign | 0.014 | 0.202028 | 0.202028 | 1343.06 |
| toy | T_add0 | 0.267 | 0.233991 | 0.233991 | 12.36 |
| toy | T_add1 | 0.001 | 0.015347 | 0.015347 | 1434.70 |
| toy | T_mod0 | 0.173 | 0.012514 | 0.012514 | 92.77 |
| toy | T_mod1 | 0.002 | 0.002680 | 0.002680 | 34.02 |
| toy | T_mul0 | 1.313 | 0.033992 | 0.033992 | 97.41 |
| toy | T_mul1 | 0.145 | 0.024333 | 0.024333 | 83.22 |
| toy | T_mul2 | 0.004 | 0.018816 | 0.018816 | 370.41 |
| toy | T_xor | 0.001 | 0.004621 | 0.004621 | 362.15 |

绝对偏差不只来自硬件环境，还来自 reference 实现的数据结构校验、数组复制、
Python 调用开销、canonical 编码、SHAKE256 以及与论文 Frodo primitive
无法完全同构的 operation mapping。

机器状态：`reference_benchmark_complete_strict_original_timing_not_reproduced`。
