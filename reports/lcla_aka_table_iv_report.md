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
| audited_preserve_dimension | T_H1 | 0.002 | 0.017195 | 0.015985 | 759.76 |
| audited_preserve_dimension | T_H2 | 0.005 | 28.223626 | 27.863608 | 564372.52 |
| audited_preserve_dimension | T_Mod | 0.837 | 0.109111 | 0.102355 | 86.96 |
| audited_preserve_dimension | T_Samp0 | 0.013 | 0.070834 | 0.065795 | 444.88 |
| audited_preserve_dimension | T_Samp1 | 0.291 | 1.553199 | 1.543751 | 433.75 |
| audited_preserve_dimension | T_Samp2 | 0.004 | 0.096638 | 0.092746 | 2315.94 |
| audited_preserve_dimension | T_Sign | 0.014 | 0.996697 | 0.971440 | 7019.26 |
| audited_preserve_dimension | T_add0 | 0.267 | 22.090979 | 21.805138 | 8173.77 |
| audited_preserve_dimension | T_add1 | 0.001 | 0.098842 | 0.095892 | 9784.23 |
| audited_preserve_dimension | T_mod0 | 0.173 | 0.723201 | 0.706441 | 318.03 |
| audited_preserve_dimension | T_mod1 | 0.002 | 0.006882 | 0.006418 | 244.11 |
| audited_preserve_dimension | T_mul0 | 1.313 | 1.039262 | 1.035772 | 20.85 |
| audited_preserve_dimension | T_mul1 | 0.145 | 0.105331 | 0.097040 | 27.36 |
| audited_preserve_dimension | T_mul2 | 0.004 | 0.026550 | 0.024677 | 563.74 |
| audited_preserve_dimension | T_xor | 0.001 | 0.007175 | 0.006854 | 617.50 |
| audited_preserve_keylen | T_H1 | 0.002 | 0.016278 | 0.015220 | 713.91 |
| audited_preserve_keylen | T_H2 | 0.005 | 22.402684 | 21.990586 | 447953.69 |
| audited_preserve_keylen | T_Mod | 0.837 | 0.099160 | 0.094706 | 88.15 |
| audited_preserve_keylen | T_Samp0 | 0.013 | 0.064014 | 0.058346 | 392.41 |
| audited_preserve_keylen | T_Samp1 | 0.291 | 1.298344 | 1.293014 | 346.17 |
| audited_preserve_keylen | T_Samp2 | 0.004 | 0.096314 | 0.092628 | 2307.85 |
| audited_preserve_keylen | T_Sign | 0.014 | 0.902544 | 0.883389 | 6346.74 |
| audited_preserve_keylen | T_add0 | 0.267 | 17.584288 | 17.328208 | 6485.88 |
| audited_preserve_keylen | T_add1 | 0.001 | 0.088974 | 0.086253 | 8797.37 |
| audited_preserve_keylen | T_mod0 | 0.173 | 0.580439 | 0.566673 | 235.51 |
| audited_preserve_keylen | T_mod1 | 0.002 | 0.005921 | 0.005590 | 196.03 |
| audited_preserve_keylen | T_mul0 | 1.313 | 0.792352 | 0.779502 | 39.65 |
| audited_preserve_keylen | T_mul1 | 0.145 | 0.089437 | 0.082996 | 38.32 |
| audited_preserve_keylen | T_mul2 | 0.004 | 0.024938 | 0.023485 | 523.45 |
| audited_preserve_keylen | T_xor | 0.001 | 0.006808 | 0.006477 | 580.82 |
| paper_performance | T_H1 | 0.002 | 0.016638 | 0.015319 | 731.89 |
| paper_performance | T_H2 | 0.005 | 22.191970 | 21.789943 | 443739.41 |
| paper_performance | T_Mod | 0.837 | 0.097530 | 0.093010 | 88.35 |
| paper_performance | T_Samp0 | 0.013 | 0.065530 | 0.059640 | 404.07 |
| paper_performance | T_Samp1 | 0.291 | 1.254026 | 1.248864 | 330.94 |
| paper_performance | T_Samp2 | 0.004 | 0.097312 | 0.092914 | 2332.79 |
| paper_performance | T_Sign | 0.014 | 0.886537 | 0.870453 | 6232.41 |
| paper_performance | T_add0 | 0.267 | 17.623368 | 17.388789 | 6500.51 |
| paper_performance | T_add1 | 0.001 | 0.088996 | 0.086039 | 8799.59 |
| paper_performance | T_mod0 | 0.173 | 0.572118 | 0.557561 | 230.70 |
| paper_performance | T_mod1 | 0.002 | 0.005981 | 0.005571 | 199.05 |
| paper_performance | T_mul0 | 1.313 | 0.822006 | 0.811384 | 37.39 |
| paper_performance | T_mul1 | 0.145 | 0.088056 | 0.082350 | 39.27 |
| paper_performance | T_mul2 | 0.004 | 0.024900 | 0.023559 | 522.51 |
| paper_performance | T_xor | 0.001 | 0.006863 | 0.006438 | 586.33 |

绝对偏差不只来自硬件环境，还来自 reference 实现的数据结构校验、数组复制、
Python 调用开销、canonical 编码、SHAKE256 以及与论文 Frodo primitive
无法完全同构的 operation mapping。

机器状态：`reference_benchmark_complete_strict_original_timing_not_reproduced`。
