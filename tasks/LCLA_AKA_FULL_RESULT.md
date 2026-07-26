# LCLA-AKA FINAL CORRECTNESS PATCH RESULT

## 状态

- 分支：`exp/LCLA-AKA-full-reproduction`
- base main：`f37bab0b18fc9952b34f3ab66354e972f6b4afc3`
- 受测实现 HEAD：`d426b477179af19ddddce628da26ce4bbfa9515d`
- 本地 evidence HEAD（RESULT 前）：
  `f48e3b60c64fa5ac9dcb6d64ffca7874411f634e`
- 首次包含 RESULT 的已通过 CI HEAD：
  `bf9721d4f8b38f113864fb0b45cc7741a89d2599`
- machine result：
  `partial_reproduction_observed_correctness_failure_constructed_backend_unverified_security`
- executable state machine implemented：true
- static relation constructed：true
- accepted session consistency：true
- honest execution correctness reproduced：false
- paper correctness claim reproduced：false
- real trapdoor reproduced：false
- strict original timing reproduced：false
- formal security verified：false

本 RESULT 自身作为独立提交，不属于上面的受测实现 HEAD。

## 本补丁提交

1. `b1ac269fccbb551e7a1fe1a2454a6817d571c90e`
   `fix: split LCLA paper and proof-consistent sampling variants`
2. `31aaf9473520e6ca450cf381fbc535ef41ff7ee4`
   `test: add unconditional LCLA correctness and Lemma3 audits`
3. `d0b98a1acbd656cee34dad1041b16c686723c970`
   `fix: remove successful-seed bias from LCLA validation and benchmarks`
4. `0020e077e698bbce11720101dc70eb30a99cbdb6`
   `fix: checkpoint unconditional LCLA correctness runs`
5. `bb7e53b07b8ff5a6c185461c8d8d7ac2d96f4355`
   `fix: preserve LCLA retry end-to-end evidence`
6. `cd1b29a053d7b689953f711e12b9bedddacb6363`
   `docs: report LCLA correctness failure and conditional-path evidence`
7. `2feb2dc4d957c37f9cf9a7b0353440439614a48b`
   `docs: record final LCLA correctness evidence`
8. `c6215a0f377a01a7b7de1f464be4e196d8b638ad`
   `docs: finalize LCLA correctness claims and audit`
9. `d426b477179af19ddddce628da26ce4bbfa9515d`
   `style: format LCLA full validator`
10. `f48e3b60c64fa5ac9dcb6d64ffca7874411f634e`
    `docs: record validated LCLA correctness status`
11. `bf9721d4f8b38f113864fb0b45cc7741a89d2599`
    `docs: record final LCLA correctness patch result`

## PDF 与版权

- PDF SHA-256：
  `5412a2962dbbbc3314cbe513d70946c0e238ba60c5debd9dfae6b7f5411bebe3`
- file page count：13
- printed pages：9213–9225
- DOI：`10.1109/JIOT.2023.3323275`
- `local_file_tracked=false`
- `ieee_republication_restricted=true`
- PDF、全文、截图和论文表格原图均未提交。

## Distribution variants

| variant | s1 | f/s2 | backend 限制 |
| --- | --- | --- | --- |
| paper_literal_distribution | uniform Zq^m | exp(-pi*k²/(2 beta²)) | programmed H1，无 TrapGen/SamplePre |
| proof_consistent_small_secret | standard lattice Gaussian | exp(-pi*k²/beta²) | programmed H1，无 TrapGen/SamplePre |
| legacy_reference | 只解释旧数据 | 不作为 paper literal | 不进入 active variant 汇总 |

每个 key pair、protocol trace、benchmark row 和关键 evidence 均记录
`distribution_variant`。

## 无条件 correctness matrix

固定连续 seed，无失败替换；每个 profile/variant 1000 次：

| profile | paper literal accepted | proof-consistent accepted |
| --- | ---: | ---: |
| toy | 0/1000 | 0/1000 |
| paper_correctness | 0/1000 | 476/1000 |
| paper_performance | 0/1000 | 779/1000 |
| audited_preserve_keylen | 0/1000 | 477/1000 |
| audited_preserve_dimension | 0/1000 | 766/1000 |
| 合计 | 0/5000 | 2498/5000 |

- honest execution attempts：10,000
- accepted：2,498
- aggregate acceptance rate：0.2498
- first-stage false reject：6,860
- final reconciliation failure：642
- unexpected other failure：0
- correctness threshold：0.999
- accepted session consistency：true
- paper correctness claim reproduced：false

Wilson 95% 区间逐组合保存在
`unconditioned_correctness_matrix.csv`。

## Lemma 3

- definition5 literal implemented：true
- prime-q counterexample found：true
- lemma3 universal correctness：false
- paper correctness proof supported：false

穷举结果：

| q | prime | violating tuples | 首个反例 |
| ---: | --- | ---: | --- |
| 7 | true | 0 | 无 |
| 11 | true | 0 | 无 |
| 15 | false | 0 | 无 |
| 31 | true | 48 | base=0, e=-2, close=27, b=0 |
| 63 | false | 336 | base=0, e=-6, close=51, b=0 |
| 127 | true | 1680 | base=0, e=-14, close=99, b=0 |

q=31、127 的反例满足论文误差界并跨越模边界；未修改 μ、Mod2、beta 或噪声。

## Intended-recipient 无条件统计

每种 variant：20 个 Bob、1000 个 request、无 seed 筛选。

| variant | target true accept | target false reject | non-target false accept | non-target true reject |
| --- | ---: | ---: | ---: | ---: |
| paper literal | 0 | 1000 | 0 | 19000 |
| proof-consistent | 876 | 124 | 0 | 19000 |

非目标误接受为 0 不掩盖目标高误拒绝，也不构成匿名性证明。

## Benchmark 语义

### Legacy raw

- 行数：49,209
- SHA-256：
  `ce1a13356801436787e02b323972542ee1e96c7b903473118747f6d2bcd4e841`
- distribution variant：`legacy_reference`
- 旧协议 phase：`conditional_success_path_latency`
- seed 搜索与失败时间：未计入

### Correctness patch exact raw

- 行数：13,021
- SHA-256：
  `80caacbea5a350d538fb2519da5bfcd0836b7ef6ee161583372b6b8950f884e2`
- actual measured success：6,272
- actual measured failure：6,743
- dependency placeholder：6
- T_Samp0/T_Samp1/T_Samp2：两种 active variant 各 1000 次
- unconditioned attempt latency：存在
- retry-until-success attempt 与 total-end-to-end：存在
- retry time included：true
- conditional success path 等价于 Table V：false

## 安全主张

- accepted_session_consistency：`executable_checked`
- honest_execution_correctness：`empirically_not_reproduced`
- lemma3_correctness：`counterexample_found`
- intended_recipient_non_target_filtering：`executable_checked`
- intended_recipient_target_availability：`empirically_not_reproduced`
- malicious KGC：`backend_not_reproduced`
- anonymity/mBR/LWE/ISIS/quantum security：未形式化验证

机器 flag：

- anonymity_formally_verified=false
- mbr_formally_verified=false
- lwe_reduction_verified=false
- isis_hardness_verified=false
- quantum_security_verified=false
- malicious_kgc_security_reproduced=false

## 门禁

- `ruff format --check .`：通过（119 files）
- `ruff check .`：通过
- `mypy`：通过（61 source files）
- `pytest`：166 passed，277.49 s
- 现有 C2LAKE 测试：包含在全量 166 tests 中，通过
- `python -m build --no-isolation`：通过
- spec validation：通过，12 expected warnings、0 unexpected errors
- security audit：通过，22 claims
- cost model：通过，3 rounds、3 packets、7 fields
- full smoke validation：通过
- full validation git commit：
  `d426b477179af19ddddce628da26ce4bbfa9515d`
- full validation git dirty：false

## GitHub push / CI / artifact

- push：成功
- 远端分支：`exp/LCLA-AKA-full-reproduction`
- CI head：`bf9721d4f8b38f113864fb0b45cc7741a89d2599`
- GitHub Actions run ID：`30202465273`
- run URL：
  `https://github.com/wyyoh/fuxian/actions/runs/30202465273`
- conclusion：`success`
- artifact：`LCLA-AKA-full-evidence`
- artifact ID：`8632122154`
- artifact size：77,134 bytes
- artifact expired：false
- artifact expires：2026-10-24T12:38:33Z
- 同一 run 中 T001、T002、T010 与 C2LAKE evidence 也均成功上传。

## 残余风险与未复现内容

- real TrapGen/SamplePre 与真实 static-key distribution；
- overwhelming-probability correctness；
- Lemma 3 universal correctness；
- Frodo native LCLA 与 strict original timing；
- mBR/LWE/ISIS/匿名性/量子安全形式证明；
- malicious KGC、PFS、KCI、UKS、NKC 形式安全；
- production CSPRNG、wire serializer、侧信道与部署审计。

当前 reference 实现不可直接用于生产部署。
