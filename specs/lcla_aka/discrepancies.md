# LCLA-AKA 已识别冲突与风险

## LCLA-D01：q 被称为素数但实际为合数
论文性能参数 `q=2^24-1=16777215`，该值为合数。audited 使用下一素数 `16777259`。

## LCLA-D02：m/n 两处不一致
正确性证明使用 m=256,n=5；性能章节使用 m=256,n=6。

## LCLA-D03：参数约束与性能参数冲突
论文写 m≥2n log q。按 log2 估算，m=256,n=6,q≈2^24 要求 m≥288，性能参数不满足。

## LCLA-D04：pk 同时表示向量与二元组
正文既写 pk=H1(ID) 向量，又写 pk=(u1,u2)。实现必须分为 pk_full 与 public_components。

## LCLA-D05：s2 被称为 partial private key 但公开发送
实现按论文公开处理，但变量命名避免将其误认为独立秘密。

## LCLA-D06：Frodo 库与 GPV trapdoor 接口未说明
论文称使用 Frodo LatticeCrypto Library，但静态密钥算法需要 TrapGen/SamplePre。必须先探测库能力，不能假设其直接提供。

## LCLA-D07：H2 多用途与编码缺失
同一 H2 同时承担 MAC、KDF 和身份掩码，且未给出字段序列化和身份长度处理。工程实现采用域分离与长度前缀。

## LCLA-D08：S() 中随机位 b 的传递不清
论文定义 S(x)=mu_b(x)，b 随机，但 transcript 只写 delta。实现需将实际 delta 完整发送并保证固定 seed 可复现，无需额外传 b；测试必须覆盖边界。

## LCLA-D09：constructed key 模式的证据边界
若外部库无法实现 TrapGen/SamplePre，可构造满足关系的密钥以复现协议层，但不得将其写成静态密钥生成完整复现。

## LCLA-D10：安全证明表述较弱
部分结论依赖哈希确定性或简化 game hopping。代码不能弥补证明不足，最终报告必须将功能验证与证明审计分开。

## LCLA-D11：Definition 5 与 Lemma 3 存在可执行反例

按论文闭区间逐字实现 `mu_0`、`mu_1` 和
`Mod2(x,S(x))=((x+S(x)(q-1)/2) mod q) mod 2` 后，在模回绕处可找到满足
`a=b+2e (mod q)` 且 `|e|<q/8-1`、但双方 `Mod2` 不相等的反例。例如
`q=127,b=0,e=-1,a=125,S(a)=mu_0(a)=0`。项目保留 literal 行为和失败统计，
不修改公式掩盖该冲突；这也限制了对论文 correctness lemma 的结论。
