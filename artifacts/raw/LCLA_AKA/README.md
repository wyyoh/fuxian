# LCLA-AKA exact raw benchmark datasets

本目录的 raw CSV 依据仓库根目录 `artifacts/README.md` 不进入 Git；仓库提交相应
SHA-256、processed summary 和本说明，不提交大体积 raw。不得让 CI smoke 覆盖
任何 exact 文件。

## `benchmark_raw.csv`（legacy reference）

- SHA-256：`ce1a13356801436787e02b323972542ee1e96c7b903473118747f6d2bcd4e841`；
- 数据行 49,209：49,200 measured-success、9 dependency placeholder；
- 统一解释为 `distribution_variant=legacy_reference`；
- 旧协议 phase 数据使用预先找到的成功 seed，语义是
  `conditional_success_path_latency`，seed 搜索/失败重试未计时；
- 不得把这些协议 phase 计时直接称为 Table V 的严格等价复现。

## `correctness_patch_benchmark_exact.csv`

- SHA-256：`80caacbea5a350d538fb2519da5bfcd0836b7ef6ee161583372b6b8950f884e2`；
- 数据行 13,021；
- `actual_measured_success_rows=6272`；
- `actual_measured_failure_rows=6743`；
- 另有 6 个 dependency-unavailable placeholder；
- 两种 active distribution variant 完全分开；
- `T_Samp0/T_Samp1/T_Samp2` 各 variant 均为 warmup 20、exact 1000 次；
- 协议计时区分 `unconditioned_attempt_latency` 与
  `retry_until_success_latency`；
- retry raw 同时保存逐次尝试和 `total_end_to_end`，并标明
  `retry_time_included=true`；
- paper literal 的 retry 达到上限仍不接受，这些失败全部保留。

benchmark class 为 `auditable_python_reference_implementation`，
`strict_original_timing_reproduced=false`。后续 exact 修改必须生成新文件/版本与新
SHA-256，不得原地删除失败或改变历史解释。
