# GPT 网页版阶段工作完成摘要

## 已冻结的实施顺序

1. 先建立仓库和证据系统。
2. 先复现 C2LAKE，因为数学依赖主要是矩阵/向量模运算。
3. C2LAKE 完成正确性后再做表 7/图 4。
4. LCLA-AKA 必须先探测 Frodo/TrapGen/SamplePre 支持。
5. 第二篇先完成 reconciliation 和 backend 分层，再写完整协议。
6. 最后进行 literal/audited 双结果报告。

## 最关键的论文冲突

### C2LAKE
- M 的 m×n 与 n×n 表述冲突；
- q 被要求为素数，但实验取 q=m²；
- d_i1、r_i 是否短向量未明确；
- Key_Agreement 计时边界未说明；
- 通信复杂度的 log 次数存在不一致。

### LCLA-AKA
- q=2^24-1=16777215 不是素数；
- 正确性 m=256,n=5，性能 m=256,n=6；
- 性能参数不满足文中 m≥2n log q；
- pk 同时表示向量和 (u1,u2)；
- s2 叫私钥却公开发送；
- 论文未说明 Frodo 库如何提供 TrapGen/SamplePre；
- H2 多用途但无域分离和编码规范。

## 第一条可直接投喂 Codex 的提示词

见 `prompts/CODEX_FIRST_PROMPT.md`。

## 第一阶段成功标准

当前不以“论文全部复现”为标准，而以：

- 规格机器可校验；
- 代码可追溯；
- C2LAKE 部分私钥验证式通过；
- literal 与 audited 不混淆；
- 遇到论文歧义不擅自猜测；

作为第一阶段门槛。
