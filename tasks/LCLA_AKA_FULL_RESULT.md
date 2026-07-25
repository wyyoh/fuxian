# LCLA-AKA FULL RESULT

## 最终状态

- 分支：`exp/LCLA-AKA-full-reproduction`
- base main：`f37bab0b18fc9952b34f3ab66354e972f6b4afc3`
- 最终实现/evidence HEAD：
  `7f5a3a740129a53429da806c8fcf95ed4846d0e2`
- machine result：
  `pass_with_partial_backend_and_partial_performance_unverified_formal_security`
- executable validation：通过
- benchmark status：partial（reference exact 完成，原始 Frodo timing 未完成）
- backend status：partial（constructed relation 可用，real trapdoor 不可用）
- formal security verified：false
- 工作树：RESULT 提交前干净

## 提交

1. `c971e2722f0df7995bc8fecd5f4ace4ba31bcba3`
   `chore: probe LCLA-AKA dependencies and Frodo capabilities`
2. `893856e2f4c7ded32c65032349a8f27b4a02ec0b`
   `feat: implement LCLA-AKA modular Gaussian and reconciliation primitives`
3. `a6701bf64f5f18b421af44f3b1d367e7a381fd77`
   `feat: implement LCLA-AKA static key backends`
4. `a956849658ecfc55e9c923c5943d35ae74a1c5fb`
   `feat: implement complete LCLA-AKA protocol`
5. `87e94df9ebcfd43df51be1c087def3e62d17a2cd`
   `test: add LCLA-AKA correctness anonymity and tamper tests`
6. `593bc3d9bd35231f5d1d17d4bc900f3ba3c45718`
   `docs: add LCLA-AKA security proof audit`
7. `c9a241b2c54d20f3bb4352e8c081557c77281be2`
   `feat: reproduce LCLA-AKA communication and cost models`
8. `849664b387cd57f717aa26f7e6b951932e231038`
   `feat: reproduce LCLA-AKA Table IV Table V and Figure 4`
9. `c2ecb9e1300b2f83740ef137b2d6b09d09df9719`
   `feat: reproduce LCLA-AKA Figures 5 and 6`
10. `1b30722c2592e1b479c251e9add7e649b2919d12`
    `docs: add complete LCLA-AKA reproduction report`
11. `207d5239a947320a737f8471eefd2ecab416d9a7`
    `ci: add LCLA-AKA full evidence checks`
12. `d28c5785d542c187088a5f9f5d307286ca16430b`
    `fix: normalize LCLA evidence CSV line endings`
13. `d64476394387d5034999e21c75f411e92e36f23a`
    `data: record LCLA-AKA exact reference benchmark`
14. `6b3d74d577063bdedecf83b37cf5250944cc3423`
    `docs: record final LCLA-AKA reproduction evidence`
15. `7f5a3a740129a53429da806c8fcf95ed4846d0e2`
    `ci: isolate full evidence outputs between protocols`

本 RESULT 文档作为独立最终说明提交，因此其提交本身不属于上面的受测实现 HEAD。

## PDF 与版权保护

- PDF SHA-256：
  `5412a2962dbbbc3314cbe513d70946c0e238ba60c5debd9dfae6b7f5411bebe3`
- file page count：13
- printed pages：9213–9225
- DOI：`10.1109/JIOT.2023.3323275`
- `git check-ignore`：
  `.gitignore:10:papers/private/`
- `local_file_tracked=false`
- `ieee_republication_restricted=true`
- 未提交 PDF、全文提取、截图、表格原图或 Figure 2–6 复制图片。

## 质量门禁

- `ruff format --check .`：通过
- `ruff check .`：通过
- `mypy`：通过（56 source files）
- `pytest`：156 passed，230.78 s（本地 Python 3.12）
- GitHub Actions pytest：通过（Python 3.11）
- `python -m build --no-isolation`：通过，sdist/wheel 成功
- spec validation：12 expected warnings，0 unexpected errors
- security audit：19 claims，形式安全 flag 全部 false
- cost model：通过，3 rounds/3 packets/7 fields
- full smoke validation：通过，failed protocol cases=0

## Backend capability matrix

| 能力/后端 | 状态 | 结论 |
| --- | --- | --- |
| NumPy safe/fast modular | available | safe 可 Python-int 回退，fast 有 overflow guard |
| reference discrete Gaussian | available | `exp(-pi*k²/beta²)`，显式 tail cutoff |
| literal S/Mod2 | available | 保留模回绕反例和失败 |
| constructed_relation | available with downgrade | programmed H1，无 trapdoor/SamplePre |
| official FrodoKEM serial build | success | GCC 13.3.0，`OPT_LEVEL=REFERENCE -j1` |
| Frodo arbitrary n,m,q | unsupported_parameter | 固定 KEM 参数，不能直接作为 LCLA backend |
| Frodo LCLA S/Mod2 | absent | reference 独立实现 |
| Frodo TrapGen | absent | real backend unavailable |
| Frodo SamplePre | absent | real backend unavailable |
| toy trapdoor | not implemented | 不以 toy 冒充 paper 参数 |

- Frodo build status：serial success；parallel `-j2` 有 KAT archive ordering race
- TrapGen status：unavailable
- SamplePre status：unavailable
- programmed H1：使用（constructed backend）
- real static key generation：0
- real backend sessions：0
- toy trapdoor sessions：0

## 协议与 reconciliation 结果

| profile/backend | attempts | accepted | NOT_INTENDED_RECEIVER | RECONCILIATION_FAILURE |
| --- | ---: | ---: | ---: | ---: |
| toy / constructed | 1000 | 7 | 922 | 71 |
| paper_correctness / constructed | 100 | 40 | 31 | 29 |
| paper_performance / constructed | 100 | 77 | 12 | 11 |
| audited_preserve_keylen / constructed | 100 | 40 | 31 | 29 |
| audited_preserve_dimension / constructed | 100 | 79 | 16 | 5 |
| 合计 | 1400 | 243 | 1012 | 145 |

- reconciliation success（accepted sessions）：243
- total detected rejection：1157
- accepted m1 consistency：true
- accepted m2 consistency：true
- accepted session key consistency：true
- audited 32-byte key consistency：true
- identity recovery：true，包括 Unicode identity
- static relation correctness：true
- literal universal correctness：未建立
- Definition 5/Lemma 3 modular-wrap counterexample：已记录

### Intended receiver

- 候选 Bob：20
- 完整试验：100 轮
- 目标 Bob：可协调 seed 上通过
- 非目标意外通过：0
- 证据边界：intended-recipient filtering executable check，不是匿名性证明。

### Tamper/结构匿名性

- `C_A/delta_A/h_A/C_B/h_B/T_A/delta_B` 单字段篡改：拒绝或最终 pair mismatch
- `A/s1/s2/f/u1/u2/pk_full/ID_A/ID_B`：静态关系、MAC、identity 或上下文检查拒绝
- plaintext identity round 1：false
- plaintext identity round 2：false
- identity masked round 3：true
- passive transcript anonymity formally verified：false

## Table IV、Table V 与 Figure 4–6

### Table IV

- paper reference：15 operations，printed page 9222，人工交叉核对
- exact profile：`paper_performance`、`audited_preserve_keylen`、
  `audited_preserve_dimension`
- warmup：20
- repetitions：1000/operation/profile
- NumPy operation measured-success：45,000
- constructed static-key measured-success：3,000
- real TrapGen/SamplePre benchmark：未完成
- strict original operation timing reproduced：false

### Table V

- paper reported：保留
- Table IV weighted reconstruction：保留
- actually measured protocol phases：每个 exact profile 100 个接受会话 × 4 phases
- phase measured-success：1,200
- Verify 独立 phase：没有伪造；Bob verification 与 reply/finish 未完全拆开
- Table IV 加权 `Num_A/Num_B=4.210/4.178 ms`
- paper Table V `Num_A/Num_B=4.255/4.233 ms`
- 差异：已并列记录，未静默修平

### Exact raw dataset

- 本地文件：`artifacts/raw/LCLA_AKA/benchmark_raw.csv`
- Git tracked：false（遵守 `artifacts/README.md`）
- SHA-256：
  `ce1a13356801436787e02b323972542ee1e96c7b903473118747f6d2bcd4e841`
- data rows：49,209
- measured-success：49,200
- measured-failure：0
- dependency-unavailable placeholder：9
- placeholder 的 `actual_execution_attempted=false`
- CI smoke 使用独立 `ci_benchmark_raw.csv`，不覆盖 exact。

### Figure

- Figure 4：reconstructed，跨 entity Spearman/单调性；不是绝对计时等价
- Figure 5：reconstructed，3 rounds/7 fields 与 bit 推导分层
- Figure 6：partial/example-fitted
- Figure 6 `entities=50,initiators=100` 示例量级：
  other 10000 rounds/5000 fields/`10^8` bits，
  LCLA 400/400/`10^7`
- Figure 6 示例与 Figure 5 每发起者 3 rounds/7 fields 冲突，未声称唯一公式。

## 安全主张状态

- mBR formally verified：false
- LWE reduction verified：false
- ISIS hardness verified：false
- anonymity formally verified：false
- quantum security verified：false
- malicious KGC formal security：未复现
- paper security proof reproduced：false
- 其他方案实际性能：未运行，`paper_reported_reference` only

## GitHub Actions 与 artifact

### 真实失败

- run ID：`30143331204`
- conclusion：failure
- 失败 step：`校验 LCLA-AKA full evidence`
- 原因：此前 C2LAKE CI validator 覆盖已跟踪的
  `artifacts/processed/C2LAKE/full_validation.json`，导致后续 LCLA validator
  观测 `git_dirty=true`。
- 修正：C2LAKE/LCLA CI full validation 均改写到各自
  `ci_full_validation.json`；没有改动协议数学或既有结论。

### 成功 run

- run ID：`30143550476`
- URL：`https://github.com/wyyoh/fuxian/actions/runs/30143550476`
- head：`7f5a3a740129a53429da806c8fcf95ed4846d0e2`
- conclusion：success
- artifact：`LCLA-AKA-full-evidence`
- artifact ID：`8615309165`
- artifact size：51,369 bytes
- artifact expired：false
- 同 run 保留并成功上传 T001、T002、T010、C2LAKE evidence。

## 论文歧义

1. q 被称为素数，但 `2^24-1` 是合数；
2. correctness 用 n=5，performance 用 n=6；
3. `paper_performance` 不满足 `m>=2nlog2(q)`；
4. tK trapdoor 的文字类型与通常 GPV trapdoor 不一致；
5. pk 同时指 whole vector 与 `(u1,u2)`；
6. s2 被称为 partial private key，但经公开信道发送；
7. H2 同时承担 MAC、mask、KDF，未给域分离；
8. identity XOR 输出长度未定义；
9. S 的随机 b 实现/传递口径不清；
10. Frodo 如何提供 TrapGen/SamplePre 未说明；
11. Definition 5/Lemma 3 在模回绕处有可执行反例；
12. mBR matching-session/Game0–Game5 文字未机械化；
13. PFS/KCI/UKS/NKC 论证简略；
14. Table IV weighted sum 与 Table V 不一致；
15. Figure 6 数量级示例与 Figure 5 公式不一致。

## 未复现内容与残余风险

- real TrapGen/SamplePre 与真实 static-key distribution；
- Frodo native LCLA operations 和 strict Table IV timing；
- universal reconciliation success；
- mBR/LWE/ISIS/匿名性/量子安全的形式证明；
- malicious KGC、PFS、KCI、UKS、NKC 的形式安全；
- production CSPRNG、wire serializer、侧信道与部署审计；
- Figure 6 唯一公式；
- 其他比较方案的实际执行性能。

当前 reference 实现不可直接用于生产部署。

## PR

- base：`main`
- compare：`exp/LCLA-AKA-full-reproduction`
- REST 创建尝试：一次
- HTTP：401 `Requires authentication`
- BLOCKER：当前环境没有可用于 GitHub REST mutation 的认证凭据
- 未重试、未伪造 PR
- compare URL：
  `https://github.com/wyyoh/fuxian/compare/main...exp/LCLA-AKA-full-reproduction?expand=1`
