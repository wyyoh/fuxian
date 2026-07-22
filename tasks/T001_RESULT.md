# Result: T001

## Summary

完成可复现仓库骨架、Python 包、质量门禁、profile YAML 加载、显式 seed RNG、
运行环境元数据采集与 JSON 写出、基础 CI，以及 sdist/wheel 打包验证。最终 30 个
基础测试在 Python 3.11.15 和 3.12.3 下均通过。未创建或实现 C2LAKE/LCLA-AKA
协议公式、密钥协商流程、外部 Frodo 集成或性能结论。

## Branch and commit

- 分支：`exp/T001-repo-scaffold`
- 决策包/main 基线：`8d7139aee23f712656bd6a41d0b5366b55fc61c8`
- 受测实现提交：`efcbe1d74bfe77ca97f97d31ffc34a60953381f5`
- 本结果文件在受测实现之后单独提交，避免用无法自引用的结果提交 SHA 代替受测 SHA。

## Files changed

- 工程与 CI：`.gitignore`、`pyproject.toml`、`.github/workflows/ci.yml`
- 包代码：`src/lattice_aka_repro/{__init__,errors,evidence,profiles,randomness}.py`
- 测试：`tests/test_{evidence,profiles,randomness}.py`
- 工具：`scripts/capture_environment.py`
- 目录说明：`artifacts/{.gitignore,README.md}`、`benchmarks/README.md`、
  `reports/README.md`
- 结果：`tasks/T001_RESULT.md`

## Commands executed

最终成功命令：

- `.venv/bin/ruff format --check .`：exit 0，9 个 Python 文件已格式化。
- `.venv/bin/ruff check .`：exit 0。
- `.venv/bin/mypy`：exit 0，9 个源文件无问题。
- `.venv/bin/python -m pytest`：exit 0，30 passed（Python 3.12.3）。
- Python 3.11.15 隔离环境中的同四项命令：均 exit 0，30 passed。
- `.venv/bin/python -m build --no-isolation`：exit 0，成功生成 sdist 与 wheel。
- 在全新 Python 3.11.15 venv 安装 wheel，并从仓库外以 `python -I` 载入
  `c2lake/toy` 与 `lcla_aka/toy`：exit 0，输出 `257` 与 `toy`。
- `scripts/capture_environment.py ...`：exit 0，生成环境 JSON。
- JSON 必填字段及 `git_dirty=false` 断言：exit 0。
- 协议实现关键字扫描与 `src/lattice_aka_repro` 文件清单检查：无越界实现。

真实失败记录及修正：

- 首轮门禁在依赖安装尚未结束时提前启动：ruff/mypy 不存在而 exit 127，pytest
  缺模块而 exit 1；依赖安装完成后重跑。
- 首轮代码门禁：格式检查 exit 1（9 文件）、lint exit 1（16 项）、mypy exit 2
  （本机 NumPy 2.5 类型桩与 3.11 目标不兼容）；pytest exit 0（27 passed）。已格式化、
  保留中文标点并忽略 `RUF001/RUF002`、改用 `datetime.UTC`，将 NumPy 收紧为
  `<2.3`，随后全部通过。
- 首次 wheel 构建虽 exit 0，但隔离审计发现未携带 profile YAML；改用 setuptools
  data files，并增加 CI wheel 安装烟测。
- `.venv/bin/python -m build` 曾因宿主缺少 `python3.12-venv/ensurepip` 而 exit 1；
  显式声明 setuptools/wheel 后使用 `--no-isolation`，构建 exit 0。

## Tests

- 总计：30 passed，0 failed，0 skipped。
- `test_profiles.py`：12 项，覆盖两个协议 toy profile、跨 cwd、未知协议/profile、
  路径穿越、来源缺失、缺字段、协议专属字段、畸形/null YAML 与返回值隔离。
- `test_randomness.py`：7 项，覆盖同 seed 一致、固定 PCG64、负 seed、bool/浮点/
  字符串/null seed 的稳定错误。
- `test_evidence.py`：11 项，覆盖必填字段、JSON round-trip、UTC/环境字段、Git
  clean/dirty、非字符串字段、计数约束与运行时 artifact 目录。
- Python 版本：3.11.15 与 3.12.3 均运行完整门禁。
- 协议测试：N/A；T001 明确禁止实现协议，未伪造协议测试。

## Evidence artifacts

- 运行时 JSON：`artifacts/processed/T001/environment.json`（按规定被 Git 忽略）。
- JSON 记录受测提交 `efcbe1d74bfe77ca97f97d31ffc34a60953381f5`、
  `git_dirty=false`、Python 3.12.3、NumPy 2.2.6、Linux
  6.17.0-35-generic、Intel Core i7-10750H 与 UTC 时间。
- 构建产物：`dist/lattice_aka_repro-0.1.0.tar.gz` 与
  `dist/lattice_aka_repro-0.1.0-py3-none-any.whl`（运行时生成并被 Git 忽略）。
- 直接/门禁依赖版本：PyYAML 6.0.3、pytest 8.4.2、ruff 0.15.22、mypy 1.20.2、
  build 1.5.0、setuptools 81.0.0、wheel 0.47.0、types-PyYAML
  6.0.12.20260518。
- T001 未运行 benchmark，因此没有伪造 raw CSV；CSV schema 留给实际 benchmark 任务。

## Profile/backend/seed

- profile：`not_applicable`
- backend：`python`
- seed：`0`
- warmup：`0`
- repetitions：`1`
- 这些值只描述 T001 环境采集，不代表任何论文参数或 benchmark。

## Deviations from specification

- 无功能性偏离。
- `RunMetadata` 在 12 个必填字段外增加可选 `git_dirty`，用于避免把未提交改动错误
  归因给纯 Git SHA；evidence schema 只规定必填字段，因此该字段是兼容扩展。
- `artifacts/raw` 与 `artifacts/processed` 均由运行时创建；未提交大文件。

## Paper ambiguities encountered

- 未触及论文公式或参数歧义。
- T001 未冻结非 benchmark 环境采集的 profile/backend/warmup/repetitions 语义；采用
  `not_applicable/python/0/1` 并显式标注。
- shared evidence 文档笼统要求每次运行同时有 JSON 与 CSV，但 T001 验收只要求环境
  JSON，且禁止性能结论；未生成没有样本含义的虚假 CSV。

## Blockers

无。

## Residual risks

- 依赖使用受限版本范围、GitHub Actions 使用 major tag，未来工具链仍可能漂移；本次
  真实版本已记录。
- 完整 profile 值类型、范围、枚举及跨规格一致性属于 T002，本轮只校验安全标识符、
  YAML 结构和必填字段。
- `capture_environment.py` 已端到端实际执行，但 CLI 参数层没有独立自动化测试。
- 环境 JSON 与构建产物按要求不入 Git，审查时需保留当前工作区或另行归档。

## Recommended next task

停止并等待 GPT 审查。未经明确授权，不启动 T002。
