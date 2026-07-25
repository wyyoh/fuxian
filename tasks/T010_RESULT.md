# Result: T010

## Summary

完成 T010 授权范围内的 C2LAKE 核心实现：模 q 向量/矩阵基础操作、shape/dtype/域校验、可重复 PCG64 实验 RNG、uniform sampler、bounded ternary sampler、Setup、SetSecretValue、PartialPrivateKeyExtract、VerifyAndAssembleKey、H1 与 H2/H3 类型化哈希接口骨架、稳定错误码、测试与 evidence。

本轮未实现 Alice/Bob 协商消息、X/Y/Z/S 协议过程、K1/K2/K3、session key agreement、eCK game、ISIS/CBi-ISIS 求解器、benchmark、Table 7、Figure 4 或任何安全性结论。

PR 创建被当前 GitHub 权限阻塞：SSH 可以推送分支，但 GitHub REST `POST /repos/wyyoh/fuxian/pulls` 返回 401 `Requires authentication`。已记录为 BLOCKER，未伪造成 PR 成功。

## Branch and commit

- 分支：`exp/T010-c2lake-core`
- 基线 main：`2764e6353b8b710df71734990062d965fe500d09`
- T010 受测代码提交：`582824c1bd22c111ad1af337b460c78a873500f2`
- T002 合并确认：main 为 `Merge pull request #2 from wyyoh/exp/T002-spec-validation`
- main GitHub Actions 确认：run `30094533889`，`completed/success`
- main T002 artifact：`T002-evidence`，artifact id `8597031473`
- PR 编号：BLOCKER，未创建；REST 创建 PR 返回 401。

## Files changed

- `papers/C2LAKE_MANIFEST.yaml`
  - 只提交论文 title、DOI、SHA-256、页数、相关页码和 `local_file_tracked:false`。
  - 未提交 PDF、全文提取结果或论文图片。
- `src/lattice_aka_repro/c2lake_core.py`
  - 新增 C2LAKE T010 核心实现与稳定错误码。
  - `M` 固定为 `n×n`，所有内部向量为 `shape=(n,)`。
  - safe backend 在 int64 累加安全时使用 NumPy，否则回退 Python int；fast backend 在最坏累加范围超出 int64 时拒绝。
  - dataclass 均为 frozen、slots；数组构造时复制并设为只读。
- `src/lattice_aka_repro/__init__.py`
  - 导出 T010 C2LAKE 核心接口。
- `tests/test_c2lake_core.py`
  - 新增 100-seed 正确性、bounded norm、determinism、safe/fast 一致性、篡改失败与稳定错误码测试。
- `scripts/validate_c2lake_core.py`
  - 生成 `artifacts/processed/T010/c2lake_core_validation.json` 与 `reports/c2lake_core_validation.md`。
  - CI 不依赖私有 PDF，仅读取已提交 manifest SHA。
- `reports/c2lake_core_validation.md`
  - 记录 T010 core evidence 摘要。
- `.github/workflows/ci.yml`
  - 保留 T001/T002 evidence。
  - 新增 T010 validate、JSON 断言和 `T010-evidence` artifact 上传。

## Commands executed

前置确认：

- `git fetch origin`：成功，拉取 main 更新。
- `git switch main`：成功。
- `git pull --ff-only origin main`：成功，main fast-forward 到 `2764e6353b8b710df71734990062d965fe500d09`。
- `git check-ignore -v papers/private/Provably_secure_lightweight_certificateless_lattic.pdf`：确认 PDF 被 `.gitignore` 忽略。
- `pdfinfo papers/private/Provably_secure_lightweight_certificateless_lattic.pdf`：确认 22 页。
- `sha256sum papers/private/Provably_secure_lightweight_certificateless_lattic.pdf`：`27502f8185258222a465750c124d1702b5a0bd387d8618f8f159b62258802e41`。

本地门禁：

- `.venv/bin/ruff format --check .`：exit 0，15 个 Python 文件已格式化。
- `.venv/bin/ruff check .`：exit 0。
- `.venv/bin/mypy`：exit 0，15 个源文件无问题。
- `.venv/bin/python -m pytest`：exit 0，59 passed。
- `.venv/bin/python -m build --no-isolation`：exit 0，sdist/wheel 构建成功。
- `.venv/bin/python scripts/validate_specs.py --repo-root .`：exit 0，T002 规格校验仍为 pass。
- `.venv/bin/python scripts/validate_c2lake_core.py --repo-root .`：exit 0，T010 core evidence 为 pass。

受测代码提交后复核：

- `python scripts/validate_c2lake_core.py --repo-root .`：exit 0。
- JSON 断言结果：
  - `result=pass`
  - `failed_cases=0`
  - `git_commit=582824c1bd22c111ad1af337b460c78a873500f2`
  - `git_dirty=false`
  - `protocol_key_agreement_implemented=false`
  - `security_proof_verified=false`

GitHub：

- branch push：成功推送 `exp/T010-c2lake-core`。
- branch push CI：run `30095885535`，`completed/success`。
- branch push artifacts：
  - `T010-evidence`，artifact id `8597572060`
  - `T002-evidence`，artifact id `8597569050`
  - `T001-evidence`，artifact id `8597568582`
- PR 创建：失败，HTTP 401 `Requires authentication`。

## Tests

- 总计：59 passed，0 failed，0 skipped。
- T010 新增测试：17 项。
- 覆盖：
  - toy、paper_literal_m32、audited_prime_m32 下各 100 个 seed：Setup 成功，部分私钥验证成功。
  - bounded ternary 输出非零，centered norm 均满足 `<= beta`。
  - 同一 seed 输出完全一致。
  - 不同 seed 不会全部产生相同结果。
  - toy 下 safe 与 fast 后端结果完全一致。
  - 篡改 ID、`d_i0`、`P_i0`、`P_i1`、`P` 后验证失败。
  - 错误 shape、错误 q、非法 profile、非法 backend 均返回稳定错误码。
  - paper_literal 合数 q 不被拒绝。
  - audited_prime 合数 q 被拒绝。
  - H1 编码对 identity、q、数组元素和 shape 敏感。
  - H2/H3 仅作为类型化接口骨架返回 `Z_q*` 标量，未实现协商逻辑。

## Evidence artifacts

- 本地 JSON：`artifacts/processed/T010/c2lake_core_validation.json`，按 artifacts 规则忽略，不提交。
- 本地报告：`reports/c2lake_core_validation.md`，已提交。
- 论文 manifest：`papers/C2LAKE_MANIFEST.yaml`，已提交。
- 私有 PDF：`papers/private/Provably_secure_lightweight_certificateless_lattic.pdf`，被 `.gitignore` 忽略，未提交。
- GitHub Actions run：`https://github.com/wyyoh/fuxian/actions/runs/30095885535`
- GitHub Actions artifact：`T010-evidence`，artifact id `8597572060`。

## Profile/backend/seed

- profiles：`toy`、`paper_literal_m32`、`audited_prime_m32`
- backend：`safe`、`fast`
- seed range：`0..99`
- warmup：`0`
- repetitions：`100`
- RNG：NumPy PCG64，仅作为可重复实验随机源，不作为生产级密码学随机数生成器。

## Deviations from specification

- PR 未创建：当前环境缺少可用于 GitHub REST 创建 PR 的认证。
- 其余 T010 实现、测试、evidence 和 CI 均按任务范围完成。

## Paper ambiguities encountered

- 未发现需要新增冻结决策的 p7–p8 公式冲突。
- 沿用 D101：`M` 固定为 `n×n`。
- 沿用 D102：不声称 `M` 满足论文中的 rank m。
- 沿用 D103/D104：`paper_literal` 与 `audited_prime` 的采样和 q 语义分离。
- p9 的 K1/K2/K3/`SK` 符号歧义不在 T010 实现范围内；本轮未实现相关部分。

## Blockers

- BLOCKER：无法创建 Pull Request。GitHub REST `POST /repos/wyyoh/fuxian/pulls` 返回 401 `Requires authentication`；当前 SSH 推送权限不足以创建 PR。
- BLOCKER：无法确认 PR checks，因为 PR 未创建。已确认同一受测 head 的 branch push GitHub Actions run `30095885535` 成功，并确认 `T010-evidence` artifact 存在。

## Residual risks

- 需要 GitHub 用户/API token 或已授权 GitHub 插件才能创建 PR 并验证 PR checks。
- T010 只验证 Setup、用户秘密值、部分私钥提取与验证组装，不验证会话协商或安全证明。

## Recommended next task

停止并等待 GPT 审查。未经明确授权，不启动 T011 或 T012。
