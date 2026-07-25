# LCLA-AKA exact raw benchmark dataset

本目录的 `benchmark_raw.csv` 是本地 exact reference reproduction dataset，但依据
仓库根目录 `artifacts/README.md` 的策略不进入 Git。

- SHA-256：`ce1a13356801436787e02b323972542ee1e96c7b903473118747f6d2bcd4e841`
- 数据行：49,209（另有 1 行 header）
- `measured_success`：49,200
- `measured_failure`：0
- `dependency_unavailable_placeholder`：9
- `actual_execution_attempted=true`：49,200
- profile：`paper_performance`、`audited_preserve_keylen`、
  `audited_preserve_dimension`，各 16,400 个 measured-success 行
- Table IV：warmup 20、repetitions 1000
- constructed protocol phases：每个 profile 100 个已验证接受会话、每会话 4 个 phase
- benchmark class：`auditable_python_reference_implementation`
- strict original timing reproduced：false

CI smoke 使用 `artifacts/processed/LCLA_AKA/ci_benchmark_raw.csv`，不会覆盖本地 exact
dataset。后续如需修改 exact 数据，必须生成新版本和新 SHA-256，不得原地伪造或删除失败。
