# 两篇格基无证书认证密钥协商论文复现：GPT 决策包 v1.0

本目录是交给 Codex 的**冻结规格与任务包**。它不是论文代码，也不宣称已经验证论文的安全证明。

目标论文：

1. **C2LAKE**：Provably secure lightweight certificateless lattice-based authenticated key exchange scheme for IIoT（2024）。
2. **LCLA-AKA**：Quantum-Safe Lattice-Based Certificateless Anonymous Authenticated Key Agreement for Internet of Things（IEEE IoT Journal, 2024）。

## 当前已完成的 GPT 网页版工作

- 建立双论文复现边界与复现等级；
- 完成两篇论文的算法流程拆解；
- 完成变量维度表；
- 完成公式到代码接口的映射；
- 识别论文中的参数、符号、维度和实验口径冲突；
- 冻结 literal / audited / toy 三类实现配置；
- 形成 Codex 的全局约束、首轮任务单和验收标准；
- 形成实验数据证据规范与复现主张矩阵。

## 使用顺序

1. 将本目录复制到新 Git 仓库根目录。
2. 将 `AGENTS.md` 作为 Codex 的仓库级强制规则。
3. 首先执行 `tasks/T001_repo_scaffold.md`。
4. 然后执行 `tasks/T002_spec_validation.md`，不得直接跳到完整协议。
5. 第一篇按 T010→T011→T012 推进。
6. 第二篇必须先执行 T020 依赖探测，再决定 TrapGen/SamplePre 后端。
7. 每轮 Codex 必须按 `templates/RESULT_TEMPLATE.md` 返回 Evidence Pack。
8. GPT 网页版使用 `prompts/GPT_REVIEW_TEMPLATE.md` 审查结果并签发下一任务。

## 核心原则

- `paper_literal`：严格照论文文字、表格和参数实现，即使存在数学疑点。
- `audited`：按本决策包记录的修正口径实现。
- `toy`：仅用于单元测试、性质测试和协议正确性排错。
- 三个配置不得混合；实验输出必须记录 profile 名称。
- 代码跑通不等于安全证明成立。
- 未经 `DECISIONS.md` 明确记录，Codex 不得自行修补论文歧义。
