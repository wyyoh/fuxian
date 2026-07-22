# Evidence Schema

每次运行必须生成 JSON 元数据和 CSV 数据。

## JSON 必填字段

```json
{
  "task_id": "Txxx",
  "git_commit": "...",
  "profile": "...",
  "backend": "...",
  "seed": 0,
  "python": "...",
  "numpy": "...",
  "os": "...",
  "cpu": "...",
  "timestamp_utc": "...",
  "warmup": 10,
  "repetitions": 100
}
```

## Benchmark CSV 必填列

- task_id
- protocol
- phase
- profile
- backend
- seed
- repetition
- elapsed_ns
- success
- error_code
- git_commit

## 报告要求

- 不删除失败样本；
- 失败样本必须解释；
- 统计值由原始 CSV 自动计算；
- 论文值不得混入 raw CSV，应在 comparison 表中单列。
