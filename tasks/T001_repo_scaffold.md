# Task ID
T001

# Objective
建立可复现仓库骨架、质量门禁、配置加载和证据输出基础，不实现任何论文协议。

# Authoritative specifications
- AGENTS.md
- DECISIONS.md
- specs/shared/evidence_schema.md

# In scope
- Python package skeleton
- pyproject.toml
- pytest/ruff/mypy 配置
- src/tests/benchmarks/artifacts/reports/scripts 目录
- profile YAML 加载器
- seed 管理器
- 环境元数据采集器
- 基础 CI

# Out of scope
- C2LAKE 数学公式
- LCLA-AKA 数学公式
- 外部 Frodo 集成
- 任何论文性能结论

# Required implementation details
1. Python 3.11+。
2. 包名建议 `lattice_aka_repro`。
3. 提供 `RunMetadata` dataclass。
4. 提供 `load_profile(protocol,name)`。
5. 提供 `seeded_rng(seed)`，禁止全局隐式 RNG。
6. 提供 JSON 元数据写出。
7. artifacts/raw 与 artifacts/processed 运行时创建，不提交大文件。
8. 添加最小 CI：ruff、mypy、pytest。

# Acceptance criteria
- `pytest` 至少 8 个基础测试通过。
- 非法 profile、缺字段、负 seed 产生稳定错误。
- 同一 seed 的 RNG 输出一致。
- 环境 JSON 满足 evidence schema。
- 不存在协议实现文件中的伪公式。

# Required evidence
按 RESULT_TEMPLATE 返回。
