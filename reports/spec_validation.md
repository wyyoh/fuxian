# 规格校验报告

## 摘要

- 结果：pass
- unexpected error：0
- expected warning：12
- profiles：c2lake=19, lcla_aka=5
- shape symbols：c2lake=25, lcla_aka=30
- claims：c2lake=14, lcla_aka=16

## 校验项

| 校验项 | 状态 | expected warning | unexpected error |
| --- | --- | ---: | ---: |
| csv_schema | pass | 0 | 0 |
| yaml_profile_schema | pass | 0 | 0 |
| parameter_relations | warning | 1 | 0 |
| prime_checks | warning | 11 | 0 |
| shape_symbol_uniqueness | pass | 0 | 0 |
| claims_class | pass | 0 | 0 |

## 必须验证项

| 项目 | 状态 | 结论 |
| --- | --- | --- |
| c2lake_n_equals_ceil_4m_log2m | pass | C2LAKE 非 toy benchmark profiles 未发现 n 关系错误。 |
| c2lake_paper_literal_q_m_squared_composite | warning | C2LAKE paper_literal q=m² 的合数情况记录为 9 个 expected warning，未拒绝。 |
| audited_q_prime | pass | 所有 q_must_be_prime=true 的 audited/toy profiles 均通过素数检查。 |
| lcla_paper_performance_dimension_relation | warning | LCLA paper_performance 的 m=256,n=6 违反 m >= 2*n*log2(q)，已记录为 expected warning。 |
| shape_symbol_uniqueness | pass | 两个 shape_table 均未发现重复 symbol。 |
| claims_class_allowed | pass | claims class 均属于允许集合或允许的组合标记。 |
| profile_family_backend_and_field_types | pass | profile family、backend、必填字段和字段类型均通过校验。 |

## Expected Warnings

| code | protocol | subject | message |
| --- | --- | --- | --- |
| C2LAKE_PAPER_Q_COMPOSITE | c2lake | paper_literal_m32 | paper_literal profile 使用合数 q；按冻结决策保留为 expected warning |
| C2LAKE_PAPER_Q_COMPOSITE | c2lake | paper_literal_m48 | paper_literal profile 使用合数 q；按冻结决策保留为 expected warning |
| C2LAKE_PAPER_Q_COMPOSITE | c2lake | paper_literal_m64 | paper_literal profile 使用合数 q；按冻结决策保留为 expected warning |
| C2LAKE_PAPER_Q_COMPOSITE | c2lake | paper_literal_m80 | paper_literal profile 使用合数 q；按冻结决策保留为 expected warning |
| C2LAKE_PAPER_Q_COMPOSITE | c2lake | paper_literal_m96 | paper_literal profile 使用合数 q；按冻结决策保留为 expected warning |
| C2LAKE_PAPER_Q_COMPOSITE | c2lake | paper_literal_m112 | paper_literal profile 使用合数 q；按冻结决策保留为 expected warning |
| C2LAKE_PAPER_Q_COMPOSITE | c2lake | paper_literal_m128 | paper_literal profile 使用合数 q；按冻结决策保留为 expected warning |
| C2LAKE_PAPER_Q_COMPOSITE | c2lake | paper_literal_m160 | paper_literal profile 使用合数 q；按冻结决策保留为 expected warning |
| C2LAKE_PAPER_Q_COMPOSITE | c2lake | paper_literal_m256 | paper_literal profile 使用合数 q；按冻结决策保留为 expected warning |
| LCLA_PAPER_PERFORMANCE_DIMENSION_CONFLICT | lcla_aka | paper_performance | LCLA paper_performance 违反 m >= 2*n*log2(q) |
| LCLA_PAPER_Q_COMPOSITE | lcla_aka | paper_correctness | paper_literal profile 使用合数 q；按冻结决策保留为 expected warning |
| LCLA_PAPER_Q_COMPOSITE | lcla_aka | paper_performance | paper_literal profile 使用合数 q；按冻结决策保留为 expected warning |

## Unexpected Errors

无。

## 范围

- 本报告只校验冻结 CSV/YAML 规格元数据。
- 本轮不实现 C2LAKE 或 LCLA-AKA 数学运算。
- 本轮不实现 TrapGen、SamplePre、密钥生成、密钥协商、benchmark 或安全性结论。
