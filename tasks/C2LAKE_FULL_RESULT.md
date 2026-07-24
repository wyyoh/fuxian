# Result: C2LAKE full reproduction

## Summary

本轮仅针对 C2LAKE 论文《Provably secure lightweight certificateless lattice-based authenticated key exchange scheme for IIoT》（DOI: `10.1002/cpe.7983`）完成完整复现链路，未启动或实现第二篇 LCLA-AKA 论文。

已完成：

- 继承 `exp/T010-c2lake-core` 的 T010 核心实现创建 `exp/C2LAKE-full-reproduction`。
- 修复 T010 遗留验证问题：空 identity、矩阵方向已知答案、safe Python-int 回退、独立部分私钥等式 oracle。
- 实现完整 C2LAKE 双方协议流程、时间戳策略、双向认证、K1/K2/K3、H3 会话密钥和 audited KDF。
- 增加完整协议正确性、篡改、重放、时间戳、上下文错误和独立数学 oracle 测试。
- 建立安全主张审计矩阵，明确区分可执行检查、论文证明范围和未形式化验证内容。
- 复现理论通信成本、存储成本、运算计数。
- 构建 Table 7 / Figure 4 benchmark 管线，完成可完成参数点的 exact 运行，并保留 m=256 超时失败记录。
- 生成完整复现报告、统一 claims matrix、summary、full validation evidence。
- 更新 CI，保留 `T001-evidence`、`T002-evidence`、`T010-evidence`，新增 `C2LAKE-full-evidence`。

未声称完成：

- eCK 安全证明形式化验证。
- ROM/forking lemma 安全归约形式化验证。
- ISIS/CBi-ISIS 困难性验证。
- 论文其他对比方案的实际运行性能复现。
- “论文安全性已由代码证明”等结论。

## Branch and Git status

- 工作分支：`exp/C2LAKE-full-reproduction`
- 继承来源：`exp/T010-c2lake-core`
- 本 RESULT 写入前分支 HEAD：`cfa1835c5e8e95fc98ab293bdfc5842742037c7d`
- 本地工作树：写入本文件前干净。
- 远端分支：已推送到 `origin/exp/C2LAKE-full-reproduction`。
- 私有 PDF：`papers/private/Provably_secure_lightweight_certificateless_lattic.pdf`，被 `.gitignore` 忽略，未提交。
- PDF ignore 证据：`.gitignore:10:papers/private/`

## Paper manifest

`papers/C2LAKE_MANIFEST.yaml` 已提交，仅记录非版权敏感元数据：

- title: `Provably secure lightweight certificateless lattice-based authenticated key exchange scheme for IIoT`
- doi: `10.1002/cpe.7983`
- sha256: `27502f8185258222a465750c124d1702b5a0bd387d8618f8f159b62258802e41`
- page_count: `22`
- relevant_pages: `7, 8`
- local_file_tracked: `false`

未提交 PDF、论文全文提取结果、论文截图或受版权保护表格图片。

## Commits

从 T010 基线之后，本轮分支包含以下提交：

1. `28a219e8dc4260a4995a500939e1cc5d83e02d7b` `fix: complete T010 independent validation`
2. `3a5f94897e7b001a36f3bfb308e6872de2d7e4a7` `feat: implement complete C2LAKE protocol`
3. `7a5116775984adfa5e3e643cedeb3767525fd983` `test: add C2LAKE protocol and attack simulations`
4. `949c269ca6eb3310657ade15af0446bee8132bbf` `docs: add C2LAKE security proof audit`
5. `a58c4bc839d7ca469cc4e04d951642c9746d715e` `feat: reproduce C2LAKE theoretical cost model`
6. `6a06f67fced9be41c7bc767463a3972017659679` `feat: reproduce C2LAKE Table 7 and Figure 4`
7. `40f1dfc36aa32316331bf1c3a4347c098797ec51` `ci: add C2LAKE full evidence checks`
8. `ac459e0ac38e97b002693d9fe271e308ff8ff47c` `docs: add complete C2LAKE reproduction report`
9. `ee631b2cfbdf241e65c147cbde2c8378a8b9b7dc` `docs: record final C2LAKE reproduction evidence`
10. `169401806d8b92fdf2284800cb9d55d5f6d68269` `docs: record final C2LAKE validation evidence`
11. `cfa1835c5e8e95fc98ab293bdfc5842742037c7d` `ci: keep C2LAKE smoke benchmark outputs isolated`

本文件作为最终结果记录单独提交。

## GitHub Actions and artifacts

已确认分支 push CI：

- run id: `30106494879`
- run URL: `https://github.com/wyyoh/fuxian/actions/runs/30106494879`
- head commit: `cfa1835c5e8e95fc98ab293bdfc5842742037c7d`
- status/conclusion: `completed/success`

Artifacts：

- `C2LAKE-full-evidence`，artifact id `8601825365`
- `T010-evidence`，artifact id `8601823256`
- `T002-evidence`，artifact id `8601819867`
- `T001-evidence`，artifact id `8601819454`

说明：本 RESULT 提交后会触发新的分支 CI。上述 run/artifact 是写入本文件前已确认成功的完整分支 CI 证据。

## Pull Request

- base: `main`
- compare: `exp/C2LAKE-full-reproduction`
- 状态：BLOCKER，未创建。
- 原因：GitHub REST `POST /repos/wyyoh/fuxian/pulls` 返回 `401 Requires authentication`。
- 已按用户指令只记录一次 REST 401 BLOCKER，未反复重试，未伪造 PR 成功。

## Local gates

最终本地门禁已执行并通过：

- `.venv/bin/python -m ruff format --check .`
- `.venv/bin/python -m ruff check .`
- `.venv/bin/python -m mypy`
- `.venv/bin/python -m pytest`
- `.venv/bin/python -m build --no-isolation`
- `.venv/bin/python scripts/validate_specs.py --repo-root .`
- `.venv/bin/python scripts/validate_c2lake_core.py --repo-root .`
- `.venv/bin/python scripts/audit_c2lake_security_claims.py --repo-root .`
- `.venv/bin/python scripts/reproduce_c2lake_cost_tables.py --repo-root .`
- `.venv/bin/python scripts/validate_c2lake_full.py --repo-root . --mode smoke`
- `.venv/bin/python scripts/reproduce_c2lake_table7.py --repo-root . --mode exact --warmup 10 --repetitions 100 --resume`
- `.venv/bin/python scripts/reproduce_c2lake_figure4.py --repo-root .`

`pytest` 结果：`92 passed`。

## Protocol correctness evidence

测试与 full validation 覆盖：

- toy：1000 个独立协议会话测试通过。
- `paper_literal_m32`：100 个独立协议会话测试通过。
- `audited_prime_m32`：100 个独立协议会话测试通过。
- full validation smoke：
  - toy: 50
  - `paper_literal_m32`: 5
  - `audited_prime_m32`: 5

显式检查结果：

- initiator authentication: passed
- responder authentication: passed
- K1 consistency: `true`
- K2 consistency: `true`
- K3 consistency: `true`
- session key scalar consistency: `true`
- audited 32-byte session key consistency: `true`
- failed protocol cases: `0`
- independent partial-private-key formula check: `passed`
- independent protocol math oracle: covered by tests
- x/y/z ephemeral secrets: 不进入公开 transcript

负向测试矩阵全部通过：

- request 字段篡改：`ID_i`、`P_i0`、`P_i1`、`X_i`、`Y_i`、`Z_i`、`S_i`、`T_i`
- response 字段篡改：`ID_j`、`P_j0`、`P_j1`、`X_j`、`Y_j`、`Z_j`、`S_j`、`T_j`
- timestamp：正常、最大年龄边界、刚超过最大年龄、最大未来偏移边界、超过未来偏移
- replay：旧 request、旧 response
- 上下文错误：q/profile/backend 不一致、identity 与 key pair 不一致、Alice/Bob key 误用、公钥分量混用、ephemeral state 与 transcript 不匹配

## Benchmark status

Exact benchmark 已按 `warmup=10`、`repetitions=100`、固定 seed schedule、`time.perf_counter_ns()`、单线程 BLAS、raw CSV 持久化和 `--resume` 方式尝试。

原始数据：

- raw CSV：`artifacts/raw/C2LAKE/benchmark_raw.csv`
- raw rows: `16200`
- success rows: `14400`
- failure rows: `1800`
- 失败行未删除，保留为 m=256 timeout 证据。

已完成参数：

- `paper_literal_m32`
- `paper_literal_m48`
- `paper_literal_m64`
- `paper_literal_m80`
- `paper_literal_m96`
- `paper_literal_m112`
- `paper_literal_m128`
- `paper_literal_m160`
- `audited_prime_m32`
- `audited_prime_m48`
- `audited_prime_m64`
- `audited_prime_m80`
- `audited_prime_m96`
- `audited_prime_m112`
- `audited_prime_m128`
- `audited_prime_m160`

未完成参数：

- `paper_literal_m256`: `timeout`
- `audited_prime_m256`: `timeout`

未用 toy 参数冒充论文参数，未静默缩小 n，未静默减少矩阵。m=256 资源/时间限制按失败行和报告记录。

生成文件：

- `artifacts/processed/C2LAKE/table7_reproduced.csv`
- `artifacts/processed/C2LAKE/table7_comparison.csv`
- `artifacts/figures/C2LAKE/figure4_reproduced.png`
- `reports/c2lake_benchmark_report.md`

## Generated reports and evidence

已新增或更新：

- `src/lattice_aka_repro/c2lake_protocol.py`
- `src/lattice_aka_repro/c2lake_cost_model.py`
- `benchmarks/c2lake_benchmark.py`
- `scripts/audit_c2lake_security_claims.py`
- `scripts/reproduce_c2lake_cost_tables.py`
- `scripts/reproduce_c2lake_table7.py`
- `scripts/reproduce_c2lake_figure4.py`
- `scripts/validate_c2lake_full.py`
- `specs/c2lake/proof_obligations.yaml`
- `specs/c2lake/paper_table7_reference.csv`
- `reports/c2lake_security_audit.md`
- `reports/c2lake_cost_reproduction.md`
- `reports/c2lake_benchmark_report.md`
- `reports/C2LAKE_FULL_REPRODUCTION.md`
- `reports/c2lake_full_validation.md`
- `artifacts/processed/C2LAKE/security_audit.json`
- `artifacts/processed/C2LAKE/cost_tables.json`
- `artifacts/processed/C2LAKE/cost_tables.csv`
- `artifacts/processed/C2LAKE/final_claims_matrix.csv`
- `artifacts/processed/C2LAKE/reproduction_summary.json`
- `artifacts/processed/C2LAKE/full_validation.json`

## Paper ambiguities and decisions

已在报告中显式记录并按 literal/audited 或冻结决策处理：

- `M` 维度/秩表述冲突：代码按冻结口径使用 `n×n`；不声称满足论文 `rank m`。
- `q` 为素数与 `q=m²` 冲突：
  - `paper_literal` 保留论文 literal 合数 q，不拒绝；
  - `audited_prime` 要求 q 为素数。
- H2/H3 列表中存在局部字段/下标笔误。
- Theorem 1 最后一行存在 `SK` 标签笔误。
- 部分安全证明依赖的短向量采样界未完全明确。
- Key_Agreement 计时边界未说明，因此 benchmark 同时报告 `initiator_total`、`responder_total`、`full_handshake`，不擅自指定其中一个等于论文口径。
- Table 7/Figure 4 的论文值仅作为只读 reference；其他方案数据标记为 `paper_reported_reference`，未声称独立复现其他方案。

## Security evidence boundary

可执行或代数检查：

- correctness
- mutual authentication 验证式
- session key agreement 一致性
- replay/timestamp 攻击模拟

论文证明或未形式化验证：

- impersonation resistance
- man-in-the-middle resistance
- known-key security
- unknown key-share resistance
- no key control
- perfect forward secrecy
- known session key security
- Type I adversary proof
- Type II adversary proof
- ISIS reduction
- CBi-ISIS reduction

明确布尔值：

- `eck_formally_verified=false`
- `rom_reduction_verified=false`
- `isis_hardness_verified=false`
- `cbi_isis_hardness_verified=false`

## Residual risks

- 当前环境无 GitHub REST 创建 PR 的认证，PR 创建被 401 阻塞。
- full validation `result=pass` 不表示完成形式安全证明；只表示可执行协议正确性、已运行 benchmark 数据有效、证据边界记录完整。
- exact benchmark 受 Python/NumPy 实现、硬件、BLAS、系统负载影响，不能期待与论文 MATLAB/硬件环境完全一致。
- m=256 两个 profile 在当前环境 timeout，属于部分实验未完成；已保留失败记录和断点续跑能力。
- 当前实现侧重复现与验证，不是生产级密码学实现；PCG64 仅为可重复实验随机源。
- 未优化大参数存储或矩阵运算；未为 Table 7 对比方案执行实际代码复现。

## Final status

除 PR 创建权限外，C2LAKE 论文复现链路、证据、报告、CI artifact 与分支推送已完成。停止等待 GPT 最终审查。不得启动 LCLA-AKA。
