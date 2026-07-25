# LCLA-AKA 外部依赖与 Frodo 能力探测

## 结论

论文引用的 Frodo 实现可定位到 Microsoft 官方 `PQCrypto-LWEKE` 项目。探测提交
`7a4e7219d06305e16aef734213001cd8fefbcc14` 在 GCC 13.3.0、GNU Make 4.3 和
Linux 环境中可用 reference 配置串行构建。

该项目实现的是固定参数 FrodoKEM，而不是 LCLA-AKA 静态密钥阶段所写的 GPV
`TrapGen/SamplePre` 接口。源码中没有 `TrapGen`、`SamplePre`、论文 Definition 5
的 `S` 或兼容 `Mod2`。因此：

- `paper_frodo_backend_built=true` 只表示官方 FrodoKEM 源码能构建；
- `frodo_native_lcla_backend_available=false`；
- `real_trapdoor_backend` 与真实 `SamplePre` 均为 unavailable；
- 后续使用 `numpy_reference` 实现数学与 reconciliation；
- 静态密钥使用明确降级的 `constructed_relation`，不得支持真实 TrapGen、
  SamplePre、恶意 KGC 或静态密钥分布复现主张；
- 严格原论文操作计时未复现。

## 来源与版本

- 论文引用：[39] J. Bos 等，*Frodo: Take off the ring! Practical,
  quantum-secure key exchange from LWE*，ACM CCS 2016。
- 官方项目页：Microsoft Research Post-quantum Cryptography Tools。
- 官方仓库：`https://github.com/microsoft/PQCrypto-LWEKE`
- 探测提交：`7a4e7219d06305e16aef734213001cd8fefbcc14`
- 许可证：MIT；仓库同时记录部分 public domain、CC0 和 BSD-3-Clause 文件。

## 构建探测

串行命令：

```text
make -C FrodoKEM OPT_LEVEL=REFERENCE -j1
```

结果为成功，产生 FrodoKEM-640/976/1344 reference 库和测试程序。并行 `-j2`
暴露 KAT archive 目标次序竞争，不能据此判定源码本身不可构建。

## 能力边界

| 能力 | 状态 | 结论 |
| --- | --- | --- |
| 模矩阵乘法 | native | Frodo 固定形状接口，需适配 |
| 矩阵/向量生成 | native | 参数和分布由 FrodoKEM 固定 |
| 离散高斯 | adaptable | 固定 CDF 噪声，不支持任意 `beta=3.192` |
| 任意 `n,m,q` | unsupported_parameter | 不支持论文参数 |
| reconciliation `S` | absent | 项目独立实现 |
| robust extractor `Mod2` | absent | 项目独立实现 |
| TrapGen | absent | real backend unavailable |
| SamplePre | absent | real backend unavailable |
| SHA/SHAKE | native | LCLA 编码和域分离仍由本项目实现 |
| XOR/bit vector | adaptable | 没有 LCLA 身份掩码 API |
| operation timing | adaptable | 与 Table IV 操作不一一对应 |
| thread control | unknown | benchmark 由环境变量限制线程 |

机器可读证据见
`artifacts/processed/LCLA_AKA/dependency_capabilities.json`，锁定信息见
`specs/lcla_aka/dependency_lock.yaml`。

## 证据限制

构建的是当前锁定的官方 FrodoKEM 代码，而论文没有说明所使用的精确代码提交、
本地修改或 Table IV 操作到库函数的映射。当前探测不能证明论文原始实现可由同一
源码严格重建，也不能把 FrodoKEM 的 KEM 操作时间当作 LCLA-AKA Table IV 时间。
