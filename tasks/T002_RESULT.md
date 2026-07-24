# Result: T002

## Summary

完成冻结规格的机器校验基础设施：CSV schema validation、YAML profile validation、
参数关系检查、素数检查、shape symbol 唯一性检查、claims class 合法性检查、
expected warning 与 unexpected error 分离、validation JSON 写出，以及
`reports/spec_validation.md` 报告生成。

前置状态已确认：GitHub 默认分支为 `main`，T001 PR #1 已合并，本地 `main` 已
快进到远端 merge commit `1dc988f1cdfd37198357e7c8e7648b9103c0dae9`，创建并使用
`exp/T002-spec-validation` 分支。本轮未启动 T010，未实现 C2LAKE 或 LCLA-AKA
协议公式、TrapGen/SamplePre、密钥生成、密钥协商、benchmark 或安全性结论。

规格校验结果为 pass：0 个 unexpected error，12 个 expected warning。

## Branch and commit

- 分支：`exp/T002-spec-validation`
- 基线 main：`1dc988f1cdfd37198357e7c8e7648b9103c0dae9`
- T002 受测提交：`d95f4f22ee75322a1c2822d9a17ddcd66026da44`
- 本结果文件在受测提交之后单独提交，避免用自引用结果提交替代受测 SHA。
- T001 PR：#1，已合并，merge commit
  `1dc988f1cdfd37198357e7c8e7648b9103c0dae9`。

## Files changed

- 新增 `src/lattice_aka_repro/spec_validation.py`：冻结规格校验模块。
- 新增 `scripts/validate_specs.py`：生成 validation JSON 与 Markdown 报告的 CLI。
- 新增 `tests/test_spec_validation.py`：覆盖 expected warning、unexpected error 分离、
  C2LAKE n 关系、audited q 素数、重复 shape symbol、非法 claims class 与非法 backend。
- 新增 `reports/spec_validation.md`：T002 人工可读规格校验报告。
- 更新 `src/lattice_aka_repro/__init__.py`：导出规格校验 API。
- 更新 `pyproject.toml`：将 shape_table.csv、claims_matrix.csv 与 parameter_profiles.yaml
  一并纳入分发包 data files。

## Commands executed

前置确认：

- `git ls-remote --symref origin HEAD`：远端 HEAD 指向 `refs/heads/main`。
- GitHub API `GET /repos/wyyoh/fuxian`：`default_branch=main`，`private=false`。
- GitHub API `GET /repos/wyyoh/fuxian/pulls?...`：PR #1 `merged_at=2026-07-24T11:05:08Z`。
- `git fetch origin && git switch main && git pull --ff-only origin main`：本地 main
  快进到 `1dc988f1cdfd37198357e7c8e7648b9103c0dae9`。
- `git switch -c exp/T002-spec-validation`：从最新 main 创建 T002 分支。

最终成功命令：

- `.venv/bin/ruff format --check .`：exit 0，12 个 Python 文件已格式化。
- `.venv/bin/ruff check .`：exit 0。
- `.venv/bin/mypy`：exit 0，12 个源文件无问题。
- `.venv/bin/python -m pytest`：exit 0，37 passed。
- `.venv/bin/python -m build --no-isolation`：exit 0，sdist/wheel 构建成功。
- `.venv/bin/python scripts/validate_specs.py --repo-root .`：exit 0，生成
  `artifacts/processed/T002/spec_validation.json` 与 `reports/spec_validation.md`。
- validation JSON 断言：exit 0，`metadata.git_commit` 等于
  `d95f4f22ee75322a1c2822d9a17ddcd66026da44`，`metadata.git_dirty=false`，
  `result=pass`，`unexpected_error_count=0`。
- 禁区关键字扫描：只命中“不实现”的范围说明，未发现协议实现文件或公式实现。

真实失败记录及修正：

- 首轮 lint：`__all__` 排序和测试 helper 中常量 `getattr` 触发 ruff；已排序并改为
  直接属性访问。
- 首轮 mypy：`_require_positive_number` 中 `object` 数值收窄不足；已改为
  `isinstance(value, (int, float)) and not isinstance(value, bool)`。
- 首轮 pytest：当前 LCLA shape_table 若把 `source` 空值视为硬错误会产生 6 个
  unexpected error；T002 要求当前规格无 unexpected error，因此将 CSV schema 硬约束
  收敛为 header 与关键字段，`source/notes` 不作为必填硬错误。
- 初版报告为英文；已按仓库中文文档约定改为中文。
- 首次 build 虽通过，但检查发现分发包只含 profile YAML，缺少 T002 校验所需 CSV；
  已将 shape_table.csv 与 claims_matrix.csv 加入 data files，随后 build 输出确认已打包。

## Tests

- 总计：37 passed，0 failed，0 skipped。
- `test_spec_validation.py` 新增 7 项：
  - 当前冻结规格 pass，12 个 expected warning，0 个 unexpected error；
  - C2LAKE benchmark `n == ceil(4*m*log2(m))` 被实际执行并能抓错；
  - audited profile 的非素数 q 被判为 unexpected error；
  - shape_table 重复 symbol 被判为 unexpected error；
  - 非法 claims class 被判为 unexpected error；
  - 非法 LCLA backend 被判为 unexpected error；
  - JSON 与 Markdown 输出可生成并包含 required findings。
- 协议测试：N/A；T002 明确禁止协议实现，未伪造协议测试。

## Evidence artifacts

- 机器 JSON：`artifacts/processed/T002/spec_validation.json`，按 artifacts 规则不提交。
- Markdown 报告：`reports/spec_validation.md`，已提交。
- JSON 结果：`result=pass`，`unexpected_error_count=0`，`expected_warning_count=12`。
- JSON 元数据：`task_id=T002`，`profile=not_applicable`，`backend=python`，
  `seed=0`，`warmup=0`，`repetitions=1`，`git_commit=d95f4f22...`，
  `git_dirty=false`。
- T002 不运行 benchmark，因此未生成没有样本语义的 CSV。

## Profile/backend/seed

- profile：`not_applicable`
- backend：`python`
- seed：`0`
- warmup：`0`
- repetitions：`1`
- 这些值只描述 T002 规格校验运行，不代表任何论文参数或 benchmark。

## Deviations from specification

- 无功能性偏离。
- CSV schema validation 校验 header 与关键字段；`notes/source` 允许为空。原因是当前
  冻结 LCLA shape_table 存在省略 source 的行，而 T002 验收要求已知冲突进入
  expected warning、当前规格不得产生 unexpected error。
- validation JSON 作为运行时 artifact 不提交；提交人工报告
  `reports/spec_validation.md`。

## Paper ambiguities encountered

- C2LAKE paper_literal `q=m²` 为合数：9 个 expected warning，未拒绝 literal。
- LCLA paper profiles 使用 `q=16777215` 合数：2 个 expected warning，未拒绝 literal。
- LCLA `paper_performance` 的 `m=256,n=6,q=16777215` 违反
  `m >= 2*n*log2(q)`：1 个 expected warning。
- C2LAKE 非 toy benchmark profiles 的 `n == ceil(4*m*log2(m))` 均通过。
- 所有 `q_must_be_prime=true` 的 audited/toy profiles 均通过素数检查。
- shape_table symbol 未发现重复；claims class 均属于允许集合或允许组合标记；
  profile family/backend/字段类型均合法。

## Blockers

无。

## Residual risks

- T002 只校验冻结规格元数据，不保证后续协议实现正确。
- LCLA 维度关系使用浮点 `log2(q)` 和 `1e-3` 容差；`paper_performance` 的冲突幅度约
  32，远超容差，结论稳定。
- CSV schema 对 `notes/source` 不做硬必填，避免把当前冻结表格的省略 source 误判为
  unexpected error；若 GPT 后续要求 source 全量补齐，应作为独立规格修订处理。

## Recommended next task

停止并等待 GPT 审查。未经明确授权，不启动 T010。
