# C2LAKE raw benchmark dataset

本目录中的 `benchmark_raw.csv` 是经批准提交的 C2LAKE exact reproduction dataset。

- 文件：`artifacts/raw/C2LAKE/benchmark_raw.csv`
- SHA-256：`d481d7ffe17e1da1cadb34f070cf6a6fe86927c42c1e8b6223243d790a7184ee`
- 语义：不可变 exact reproduction dataset
- 生成模式：`mode=exact`
- warmup：`10`
- repetitions：`100`
- CI smoke 策略：CI 不允许覆盖该文件；CI smoke 输出必须写入 `artifacts/processed/C2LAKE/ci_*`

后续如果需要修正或扩展 raw benchmark 数据，必须生成新文件或新版本，并更新对应 SHA-256 manifest。不得无说明地覆盖本文件。
