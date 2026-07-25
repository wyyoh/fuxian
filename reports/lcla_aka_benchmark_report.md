# LCLA-AKA Table IV、Table V 与 Reference Benchmark

## 实现口径

- `benchmark_class=auditable_python_reference_implementation`。
- FrodoKEM serial build 成功，但未提供 LCLA 所需任意参数、TrapGen、SamplePre、
  S/Mod2；所以 `strict_original_operation_timing_reproduced=false`。
- NumPy reference 包含 dataclass/shape/domain/overflow 检查、数组复制、
  canonical hash encoding、SHAKE256、Python 对象与函数调用开销。
- constructed phase 计时只选取预先确认可接受的 seed；seed 搜索不计时，
  当前协议 API 内的静态关系验证开销会计入。

## Table V 分层结果

| scheme | profile | evidence | Num_A ms | Num_B ms | Sum ms | Verify ms |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| Feng et al. [23] | paper_reference | paper_reported_reference | 2.102 | 2.096 | 4.198 | 2.091 |
| Dabra et al. [34] | paper_reference | paper_reported_reference | 2.7 | 2.403 | 5.103 | 2.398 |
| Ding et al. [35] | paper_reference | paper_reported_reference | 2.873 | 2.495 | 5.368 | 2.49 |
| LCLA-AKA | paper_reference | paper_reported_reference | 4.255 | 4.233 | 8.448 | 1.025 |
| LCLA-AKA | paper_performance | reconstructed_from_table_iv | 4.21 | 4.178 | 8.388 | 0.989 |
| LCLA-AKA | paper_performance | numpy_reference_reconstructed_from_operations | 121.493736 | 119.528263 | 241.021999 | 21.128289 |
| LCLA-AKA | paper_performance | actually_measured_protocol_phases | 147.4389315 | 145.43500799999998 | 292.8739395 |  |
| LCLA-AKA | toy | numpy_reference_reconstructed_from_operations | 2.8429794999999998 | 2.3775355 | 5.220515 | 0.43916449999999996 |

由 Table IV 三位小数逐项乘 Num_A/Num_B 后得到 4.210/4.178 ms，
与 Table V 的 4.255/4.233 ms 不一致；可能来自未显示的小数、额外开销或排版。
两组值并列保留。Verify 的 Table IV 重构公式也标明 scope，不能与论文值混同。

协议 phase 的 Bob verification 与 reply、Bob finish 未被进一步拆开，
因此 actually measured 行不伪造独立 Verify 数值。

机器状态：`table_v_reconstructed_with_non_equivalent_reference_measurements`。
