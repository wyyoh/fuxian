# LCLA-AKA 通信与理论成本复现

## 口径结论

- 协议是 3 个网络轮次、3 个 packet、7 个论文统计字段；7 不是网络 packet 数。
- `paper_compact_message_bits` 按每个 Zq 元素的最小位长和论文 m-bit identity 假设推导。
- `canonical_hash_encoding_bytes` 仅是当前 SHAKE transcript 的类型化长度前缀编码。
- `network_wire_encoding_defined=false`；项目没有专用网络 wire serializer。
- 因此 canonical hash encoding 不能直接用于验证或否定论文通信效率主张。

## 通信结果

| profile | m | n | q | 紧凑位数 | 实际 identity 紧凑位数 | canonical hash bytes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| toy | 32 | 2 | 127 | 14496 | 14608 | 2817 |
| paper_correctness | 256 | 5 | 16777215 | 3147008 | 3146896 | 394185 |
| paper_performance | 256 | 6 | 16777215 | 3147008 | 3146896 | 394185 |
| audited_preserve_keylen | 256 | 5 | 16777259 | 3278080 | 3277968 | 525295 |
| audited_preserve_dimension | 288 | 6 | 16777259 | 4148640 | 4148496 | 664593 |

紧凑位数推导为 `2*m^2*ceil(log2(q)) + 4*m + identity_bits`：
`C_A/C_B` 各含 `m^2` 个 Zq 元素；`delta_A/h_A/h_B/delta_B` 各 m bits；
`T_A` 长度等于 Alice identity 的字节长度。

## 存储边界

JSON/CSV 同时报告数学理想位长与 NumPy int64 实际数组字节数。
真实 TrapGen/SamplePre 不可用，trapdoor 的结构和存储量标为 unavailable，
不使用普通短向量冒充。

## 运算计数

按 setup、静态密钥生成/验证、Alice create、Bob verify/reply、Alice finish、
Bob finish 与 full handshake 分阶段统计矩阵乘、矩阵向量乘、加减、标量乘、
离散高斯、S、Mod2、H1、各 H2 分域及 XOR。计数是高层原语次数，
不等同于底层标量乘加数，也不是论文 Frodo 原生计时。
