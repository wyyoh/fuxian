# GPT 审查输入要求

请提供：

- 当前任务单；
- Codex RESULT 文件；
- git diff；
- 测试输出；
- 生成的 CSV/JSON/报告；
- blocker。

# GPT 审查框架

1. 是否严格限定在 scope？
2. 是否违反 DECISIONS 或 AGENTS？
3. 数学式、shape、域和采样是否一致？
4. 测试是否真正验证性质，而非复述实现？
5. literal 与 audited 是否隔离？
6. 是否存在硬编码、mock 或静默降级？
7. 证据是否可追溯？
8. 是否可合并？

# 输出格式

## Verdict
APPROVE / APPROVE_WITH_FIXES / REJECT

## Blocking issues

## Non-blocking issues

## Required patch task

## Verified claims

## Claims still unverified

## Next task authorization
只签发一个下一任务。
