# LCLA-AKA Figure 5/6 公式审计

## 结论

Figure 5 的单发起者文字给出了部分明确关系：LCLA-AKA 为 3 个网络轮次、
7 个统计字段；Feng 等方案为 `3n+4` 个“message”，Dabra/Ding 为 `3n+5`；
其他方案需要 `n+2` 轮。这里把论文的“7 messages”解释为三个 packet 中的七个字段，
以避免与协议三轮状态机冲突。

Figure 6 只给出三组数量级示例，没有列出曲面公式和具体坐标。将
`entities=50, initiators=100` 解释为叙述中的最大示例，可以拟合出 10000 轮、
5000 个字段和 `10^8` bits，以及 LCLA 的 400/400/`10^7`。这些拟合公式与
Figure 5 的 3 轮、7 字段以及本项目字段级通信量并不一致。因此 Figure 6 状态是
`partial`，图上使用 `paper_narrative_example_fitted`，不能称为唯一或严格复现。

## Figure 5

| 曲线 | 公式 | 来源 | 已核对示例 | 歧义 | 状态 |
| --- | --- | --- | --- | --- | --- |
| LCLA rounds | `3` | printed p9223 文字 | 任意实体数为 3 | 无 | paper reported |
| LCLA fields | `7` | printed p9223 文字 | 任意实体数为 7 | 论文称 message，本项目称字段 | reinterpreted |
| LCLA bits | `2*m²*bitlen(q)+5m` | 七字段推导 | m=256 得 3,147,008 bits | 论文图坐标未列表 | reconstructed |
| other rounds | `entities+2` | printed p9221 `n+2` | 文字关系 | n 的索引不明 | reconstructed |
| Feng fields | `3*entities+4` | printed p9221 | 明文公式 | message/field 口径 | paper reported |
| Dabra/Ding fields | `3*entities+5` | printed p9221 | 明文公式 | message/field 口径 | paper reported |
| other bits | `sender_bits+(entities-1)*receiver_bits` | p9223 双方 bit 数 | entities=2 恢复 8448/13064/16672 | 广播是否按接收者重复计数不明 | partial |

## Figure 6

| 曲线 | 拟合公式 | 核对示例 E=50,I=100 | 歧义 | 状态 |
| --- | --- | ---: | --- | --- |
| other rounds | `2*E*I` | 10000 | 曲面公式未给出 | example-fitted partial |
| other fields | `E*I` | 5000 | 与 Figure 5 字段公式不能同时直接成立 | example-fitted partial |
| other bits | `20000*E*I` | 100000000 | 只核对数量级 | example-fitted partial |
| LCLA rounds | `4*I` | 400 | 与每发起者 3 轮冲突 | example-fitted conflicting |
| LCLA fields | `4*I` | 400 | 与每发起者 7 字段冲突 | example-fitted conflicting |
| LCLA bits | `100000*I` | 10000000 | 与字段级 3,147,008 bits/发起者冲突 | example-fitted conflicting |

所有绘图坐标均由提交的 CSV 生成，没有复制论文图片，也没有用目测坐标伪装。
