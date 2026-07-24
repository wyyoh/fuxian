# Result: T001-PATCH

## Summary

完成 T001-PATCH 中可由当前权限执行的修复：保留 `main` 为基线提交
`8d7139aee23f712656bd6a41d0b5366b55fc61c8`，保留并继续使用
`exp/T001-repo-scaffold` 工作分支，补充公开仓库 PDF/私有论文忽略规则，并更新
GitHub Actions，使其在既有质量门禁后生成 T001 evidence JSON 并上传
`T001-evidence` artifact。

未启动 T002，未实现任何 C2LAKE 或 LCLA-AKA 协议公式。

PR 创建和默认分支修改均被当前 GitHub 权限阻塞：SSH deploy key 可推送代码，但
GitHub REST API 返回 401，不能创建 PR，也不能把默认分支从
`exp/T001-repo-scaffold` 改为 `main`。该状态按要求记录为 BLOCKER，未伪造成成功。

## Branch and commit

- 工作分支：`exp/T001-repo-scaffold`
- 稳定 `main` 分支：本地 `main` 与 `origin/main` 均指向
  `8d7139aee23f712656bd6a41d0b5366b55fc61c8`
- 远端默认分支查询结果：`exp/T001-repo-scaffold`
- T001 原实现提交：`efcbe1d74bfe77ca97f97d31ffc34a60953381f5`
- T001 原结果提交：`6e82b219255056d168017008e3ab6bd7affbe5ac`
- T001-PATCH 受测 head commit：`48da6c9e9a859121d219f40c2fd7891c929cf444`
- 本结果文件在受测 head 之后更新，避免把自引用文档提交伪装为受测提交。
- PR 编号：BLOCKER，未创建；`POST /repos/wyyoh/fuxian/pulls` 返回 401
  `Requires authentication`。

## Files changed

- `.gitignore`
  - 增加 `papers/private/`
  - 增加 `papers/**/*.pdf`
- `.github/workflows/ci.yml`
  - 保留既有 ruff format、ruff check、mypy、pytest、build、wheel profile 烟测。
  - 新增 `scripts/capture_environment.py` 调用，写出
    `artifacts/processed/T001/environment.json`。
  - 新增 JSON 断言：`git_commit == git rev-parse HEAD` 且 `git_dirty is False`。
  - 新增 `actions/upload-artifact@v4`，artifact 名称 `T001-evidence`。
- `tasks/T001_RESULT.md`
  - 增加 T001-PATCH 的 PR、CI、受测 head、artifact、默认分支处理和真实失败记录。

## Commands executed

本地成功命令：

- `.venv/bin/ruff format --check .`：exit 0，9 个 Python 文件已格式化。
- `.venv/bin/ruff check .`：exit 0。
- `.venv/bin/mypy`：exit 0，9 个源文件无问题。
- `.venv/bin/python -m pytest`：exit 0，30 passed。
- `.venv/bin/python -m build --no-isolation`：exit 0，成功生成 sdist 与 wheel。
- `.venv/bin/python -c 'import yaml; ...'`：exit 0，workflow YAML 可解析。
- Python 3.11.15 临时环境安装 wheel 后，从仓库外以 `python -I` 载入
  `c2lake/toy` 与 `lcla_aka/toy`：exit 0，输出 `wheel smoke ok`。
- `scripts/capture_environment.py ...`：exit 0，生成本地 evidence JSON。
- JSON 断言：exit 0，`git_commit` 等于
  `48da6c9e9a859121d219f40c2fd7891c929cf444`，`git_dirty=false`。
- `git push origin exp/T001-repo-scaffold`：exit 0，远端工作分支更新到
  `48da6c9e9a859121d219f40c2fd7891c929cf444`。
- `git ls-remote --symref origin HEAD`：exit 0，确认远端默认分支仍为
  `exp/T001-repo-scaffold`。

GitHub API 与 CI 查询：

- `GET /repos/wyyoh/fuxian`：status 200，`private=false`，
  `default_branch=exp/T001-repo-scaffold`。
- `PATCH /repos/wyyoh/fuxian` 设置 `default_branch=main`：status 401，
  `Requires authentication`。
- `POST /repos/wyyoh/fuxian/pulls` 创建 `exp/T001-repo-scaffold -> main` PR：
  status 401，`Requires authentication`。
- `GET /repos/wyyoh/fuxian/actions/runs?...`：status 200，branch push CI run
  `30087424342` 已完成且 `conclusion=success`。
- `GET /repos/wyyoh/fuxian/actions/runs/30087424342/artifacts`：status 200，
  artifact `T001-evidence` 存在且未过期。

真实失败记录及修正：

- GitHub 默认分支修改失败：REST API 返回 401。原因是当前只有 SSH deploy key
  推送权限，没有 GitHub 用户/API token。未修正，列为 BLOCKER。
- GitHub PR 创建失败：REST API 返回 401。原因同上。未修正，列为 BLOCKER。
- 本机 `.venv/bin/python -m venv /tmp/...` wheel 烟测失败：宿主缺
  `python3.12-venv/ensurepip`，导致临时 venv 无 pip。改用 `uv venv --python 3.11`
  与 `uv pip install --python ...` 后，Python 3.11.15 wheel 烟测通过。
- 本机 PATH 中无 `python3.11` 命令；使用 `uv` 提供 CPython 3.11.15 运行时完成
  CI 目标版本的本地烟测。

## Tests

- 本地 Python 3.12.3：30 passed，0 failed，0 skipped。
- Python 3.11.15 wheel 烟测：通过。
- GitHub Actions branch push run：`quality-gates`，run id `30087424342`，
  head `48da6c9e9a859121d219f40c2fd7891c929cf444`，status `completed`，
  conclusion `success`。
- PR checks：BLOCKER；PR 未能创建，因此不存在 PR checks 可验证。
- 协议测试：N/A；T001/T001-PATCH 均禁止实现协议，未伪造协议测试。

## Evidence artifacts

- 本地运行时 JSON：`artifacts/processed/T001/environment.json`，按规则被 Git 忽略。
- 本地 JSON 记录受测提交
  `48da6c9e9a859121d219f40c2fd7891c929cf444` 与 `git_dirty=false`。
- GitHub Actions artifact 名称：`T001-evidence`。
- GitHub Actions run：`https://github.com/wyyoh/fuxian/actions/runs/30087424342`
- Artifact API：`https://api.github.com/repos/wyyoh/fuxian/actions/artifacts/8594288789/zip`
- T001-PATCH 没有 benchmark，因此未生成没有样本含义的伪 CSV。

## Profile/backend/seed

- profile：`not_applicable`
- backend：`python`
- seed：`0`
- warmup：`0`
- repetitions：`1`
- 这些值只描述 T001/T001-PATCH 环境采集，不代表任何论文参数或 benchmark。

## Deviations from specification

- PR 创建未完成：当前权限无法通过 GitHub REST API 创建 PR，按要求列为 BLOCKER。
- 默认分支未改为 `main`：当前权限无法修改 GitHub 仓库默认分支，按要求列为 BLOCKER。
- `main` 分支本身已稳定存在于本地和远端，均指向基线提交
  `8d7139aee23f712656bd6a41d0b5366b55fc61c8`。
- CI 在 branch push 上已通过；PR checks 因 PR 创建失败无法验证。

## Paper ambiguities encountered

- 未触及论文公式、协议流程或参数歧义。
- 未启动 T002。

## Blockers

- BLOCKER：无法修改 GitHub 默认分支。`PATCH /repos/wyyoh/fuxian` 返回 401
  `Requires authentication`；SSH deploy key 不能执行该 REST 管理操作。
- BLOCKER：无法创建 Pull Request。`POST /repos/wyyoh/fuxian/pulls` 返回 401
  `Requires authentication`；SSH deploy key 不能创建 PR。
- BLOCKER：无法确认 PR 上 checks 全部通过，因为 PR 未创建。已确认同一受测 head 的
  branch push Actions run `30087424342` 成功。

## Residual risks

- 当前 GitHub 默认分支仍是 `exp/T001-repo-scaffold`，需要仓库管理员或 GitHub
  用户/API token 才能改为 `main`。
- 需要仓库管理员或 GitHub 用户/API token 才能创建 PR 并验证 PR checks。
- 后续如果改动结果文件本身并推送，会触发新的 branch push CI run；该自引用问题不会
  改变受测代码提交 `48da6c9e9a859121d219f40c2fd7891c929cf444` 的 CI 结果。

## Recommended next task

停止并等待 GPT 审查。未经明确授权，不启动 T002。
