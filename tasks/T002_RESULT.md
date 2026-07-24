# Result: T002-PATCH

## Summary

完成 T002-PATCH 中可由当前权限执行的修复：修正 LCLA shape_table 中 6 个
symbol 的 notes/source 错位，恢复 shape_table `source` 必填校验，加固
`audited`/`audited_prime` profile 的 `q_must_be_prime=true` 与实际素数要求，补齐
GitHub Actions 中的 T002 evidence 生成、校验与 `T002-evidence` artifact 上传。

规格校验结果保持 pass：12 个 expected warning，0 个 unexpected error。T001 evidence
在 CI 中保留，但不替代 T002 evidence。本轮未启动 T010，未实现协议公式、密钥生成、
密钥协商、TrapGen、SamplePre 或 benchmark。

PR 创建被当前 GitHub 权限阻塞：SSH deploy key 可以推送分支，但 GitHub REST
`POST /repos/wyyoh/fuxian/pulls` 返回 401 `Requires authentication`。已如实记录为
BLOCKER，未伪造成 PR 成功。

## Branch and commit

- 分支：`exp/T002-spec-validation`
- 基线 main：`1dc988f1cdfd37198357e7c8e7648b9103c0dae9`
- T002 原受测提交：`d95f4f22ee75322a1c2822d9a17ddcd66026da44`
- T002 原结果提交：`53819e3bda4b4d13a25401fe6e6d22d5c1136137`
- T002-PATCH 受测代码提交：`f18262ddd7ab7ef082a514fd22c992a5db82599b`
- 本结果文件在受测代码提交之后单独提交，避免用自引用结果提交替代受测 SHA。
- PR 编号：BLOCKER，未创建；创建 PR 的 REST 请求返回 401。

## Files changed

- `.github/workflows/ci.yml`
  - 保留原有 ruff、mypy、pytest、build、wheel smoke 与 T001 evidence。
  - 新增 `python scripts/validate_specs.py --repo-root .`。
  - 新增 T002 JSON 断言：`result=="pass"`、`unexpected_error_count==0`、
    `metadata.git_commit == git rev-parse HEAD`、`metadata.git_dirty == false`。
  - 新增 `actions/upload-artifact@v4` 上传 `T002-evidence`。
- `specs/lcla_aka/shape_table.csv`
  - 修正 `E_A`、`e_A`、`X_B`、`E_B`、`e_B`、`SK` 六行的 notes/source 错位。
  - 当前每一行均严格为 8 列。
- `src/lattice_aka_repro/spec_validation.py`
  - shape_table `source` 恢复为必填，`notes` 继续允许为空。
  - CSV 额外列产生 `CSV_ROW_WIDTH_INVALID` unexpected error。
  - audited/audited_prime family 禁止将 `q_must_be_prime` 改成 false 绕过检查。
  - audited/audited_prime family 的 q 必须实际为素数。
- `tests/test_spec_validation.py`
  - 新增 source 为空、audited flag false、非法 family、非法数值类型等负向测试。
- `reports/spec_validation.md`
  - 更新 audited prime 必检项说明。
- `tasks/T002_RESULT.md`
  - 记录本次 patch、CI、artifact、BLOCKER 与真实失败。

## Commands executed

成功命令：

- `.venv/bin/ruff format --check .`：exit 0，12 个 Python 文件已格式化。
- `.venv/bin/ruff check .`：exit 0。
- `.venv/bin/mypy`：exit 0，12 个源文件无问题。
- `.venv/bin/python -m pytest`：exit 0，42 passed。
- `.venv/bin/python -m build --no-isolation`：exit 0，sdist/wheel 构建成功。
- `.venv/bin/python scripts/validate_specs.py --repo-root .`：exit 0，生成
  `artifacts/processed/T002/spec_validation.json` 与 `reports/spec_validation.md`。
- validation JSON 断言：exit 0，`result=pass`、`unexpected_error_count=0`、
  `expected_warning_count=12`、`metadata.git_commit=f18262ddd7ab...`、
  `metadata.git_dirty=false`。
- LCLA shape_table 宽度检查：exit 0，所有行均为 8 列。
- GitHub Actions branch push run `30089953225`：`completed/success`。
- GitHub Actions artifacts 查询：run `30089953225` 中存在 `T002-evidence`
  artifact id `8595260709`，同时保留 `T001-evidence` artifact id `8595260373`。

真实失败记录及修正：

- T002 主体审查指出 LCLA shape_table 6 行 source 错位且 source 未硬校验；已修正 CSV，
  并恢复 `source` 必填，新增 source 为空的负向测试。
- T002 主体审查指出 audited prime 可通过 `q_must_be_prime=false` 绕过；已将
  audited/audited_prime family 的 flag 与实际素数检查绑定，新增 C2LAKE 与 LCLA 负向测试。
- T002 主体审查指出 CI 缺少 T002 evidence；已新增 T002 validate、JSON 断言与
  `T002-evidence` artifact 上传。
- PR 创建失败：`POST /repos/wyyoh/fuxian/pulls` 返回 401 `Requires authentication`。
  当前 SSH deploy key 不能创建 PR；GitHub 插件安装请求未获确认。未修正，列为 BLOCKER。

## Tests

- 总计：42 passed，0 failed，0 skipped。
- 新增覆盖：
  - 当前修复后的规格仍为 12 个 expected warning、0 个 unexpected error。
  - 任意 shape row 的 `source` 为空时产生 `CSV_REQUIRED_FIELD_EMPTY` unexpected error。
  - `audited_prime_m32.q_must_be_prime=false` 产生 unexpected error。
  - LCLA audited profile 的 `q_must_be_prime=false` 产生 unexpected error。
  - 非法 profile family 被拒绝。
  - `m` 非法字段类型被拒绝。
- 协议测试：N/A；T002-PATCH 禁止协议实现，未伪造协议测试。

## Evidence artifacts

- 本地机器 JSON：`artifacts/processed/T002/spec_validation.json`，按 artifacts 规则不提交。
- Markdown 报告：`reports/spec_validation.md`，已提交。
- 本地 JSON 记录：`git_commit=f18262ddd7ab7ef082a514fd22c992a5db82599b`，
  `git_dirty=false`，`result=pass`，`unexpected_error_count=0`，
  `expected_warning_count=12`。
- GitHub Actions run：`https://github.com/wyyoh/fuxian/actions/runs/30089953225`
- GitHub Actions artifact：`T002-evidence`，artifact id `8595260709`。
- T002-PATCH 不运行 benchmark，因此未生成没有样本语义的 CSV。

## Profile/backend/seed

- profile：`not_applicable`
- backend：`python`
- seed：`0`
- warmup：`0`
- repetitions：`1`
- 这些值只描述 T002/T002-PATCH 规格校验运行，不代表任何论文参数或 benchmark。

## Deviations from specification

- PR 创建未完成：当前权限无法通过 GitHub REST API 创建 PR，按实际情况列为 BLOCKER。
- PR checks 未能确认：PR 未创建，因此不存在 PR checks 可验证。已确认同一受测 head 的
  branch push GitHub Actions run `30089953225` 成功，并确认 `T002-evidence` 存在。
- 其余 T002-PATCH 修复均按要求完成。

## Paper ambiguities encountered

- C2LAKE paper_literal `q=m²` 为合数：9 个 expected warning，仍未拒绝 literal。
- LCLA paper profiles 使用 `q=16777215` 合数：2 个 expected warning，仍未拒绝 literal。
- LCLA `paper_performance` 的 `m=256,n=6,q=16777215` 违反
  `m >= 2*n*log2(q)`：1 个 expected warning。
- 未新增论文公式或协议口径判断。

## Blockers

- BLOCKER：无法创建 Pull Request。GitHub REST
  `POST /repos/wyyoh/fuxian/pulls` 返回 401 `Requires authentication`；当前 SSH
  deploy key 只具备 Git 推送权限，不能创建 PR。
- BLOCKER：无法确认 PR 上 GitHub Actions 全部成功，因为 PR 未创建。已确认 branch
  push run `30089953225` 成功并上传 `T002-evidence`。

## Residual risks

- 需要 GitHub 用户/API token 或已授权的 GitHub 插件才能创建 PR 并验证 PR checks。
- 本轮只校验冻结规格元数据，不保证后续协议实现正确。

## Recommended next task

停止并等待 GPT 审查。未经明确授权，不启动 T010。
