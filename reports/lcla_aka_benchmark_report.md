# LCLA-AKA Reference Benchmark 与条件路径口径审计

## 结论

本项目的 benchmark class 是 `auditable_python_reference_implementation`。
FrodoKEM serial build 成功，但没有论文所需的 arbitrary 参数、TrapGen、
SamplePre 或 LCLA S/Mod2，因此：

- `strict_original_operation_timing_reproduced=false`；
- NumPy reference 时间不能写成 Frodo 原实现的严格复现；
- 旧 Table V protocol phase 数据是 `conditional_success_path_latency`；
- seed 搜索和失败重试未包含在旧数据中，不能与论文 Table V 直接等价。

## 分布修订后的 exact 数据

新 raw `correctness_patch_benchmark_exact.csv` 完全区分：

- `paper_literal_distribution`；
- `proof_consistent_small_secret`。

它包含 13,021 行，SHA-256 为
`80caacbea5a350d538fb2519da5bfcd0836b7ef6ee161583372b6b8950f884e2`。
其中实际测量成功 6,272 行、实际测量失败 6,743 行，另有 6 个依赖不可用
placeholder。失败不删除，placeholder 不计作独立执行失败。

受 Gaussian 口径影响的 `T_Samp0/T_Samp1/T_Samp2` 对两种 active variant
分别以 warmup 20、repetitions 1000 重测。协议计时新增：

1. `unconditioned_attempt_latency`：连续 seed，成功和失败均保留；
2. `retry_until_success_latency/attempt`：每次失败及成功尝试分别计时；
3. `retry_until_success_latency/total_end_to_end`：包含失败、搜索/重试和最终
   成功或达到上限的总时间；
4. expected cost：使用无条件 acceptance probability、mean attempt latency 与
   `1/p` 推导；当 `p=0` 时不伪造有限成功成本。

所有 retry 行标记 `retry_time_included=true`。processed summary 不再排除
`total_end_to_end` 行。

## 旧 49,209 行数据

`benchmark_raw.csv` 保留用于历史解释，整体标为 `legacy_reference`。其协议 phase
来自预先确认接受的 seed；这类数据可描述一次成功路径的函数耗时，但不能代表无条件
协议正确性、重试成本或预期成功成本。

## Table V 分层结果

| scheme/profile | evidence | Num_A ms | Num_B ms | Sum ms | Verify ms |
| --- | --- | ---: | ---: | ---: | ---: |
| LCLA-AKA paper | paper_reported_reference | 4.255 | 4.233 | 8.448 | 1.025 |
| LCLA-AKA paper | reconstructed_from_table_iv | 4.210 | 4.178 | 8.388 | 0.989 |
| paper_performance | legacy conditional success path | 151.554 | 148.980 | 300.534 | 未独立测量 |
| audited_preserve_keylen | legacy conditional success path | 152.360 | 149.514 | 301.875 | 未独立测量 |
| audited_preserve_dimension | legacy conditional success path | 193.890 | 189.938 | 383.828 | 未独立测量 |

Table IV 三位小数加权结果与论文 Table V 自身不一致；两组数据并列保留。
Python reference 还包含 dataclass、shape/dtype/domain/overflow 校验、数组复制和
只读转换、canonical encoding、SHAKE256 及 Python 调用开销，因此绝对偏差不能只
归因于硬件或操作系统。

机器状态为
`table_v_reconstructed_with_non_equivalent_reference_measurements`。
