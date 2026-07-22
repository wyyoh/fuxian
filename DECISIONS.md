# 决策日志

## 通用决策

### D001：复现配置分离
采用 `paper_literal`、`audited`、`toy` 三类 profile。任何运行结果必须携带 profile。

### D002：参考实现优先
第一阶段使用清晰的 NumPy/Python 数学实现；原生库只作为可选 benchmark backend。

### D003：哈希实现
协议工程实现使用 SHAKE256 + 显式域分离 + 长度前缀序列化。  
这用于实现确定性随机预言机接口，不等同于形式安全证明中的可编程随机预言机。

### D004：模运算
每个矩阵/向量乘法后立即模 q。参考模式提供溢出安全检查；benchmark 模式允许在已证明 int64 安全的参数范围使用 NumPy int64。

### D005：时间测量
使用 `time.perf_counter_ns()`；先 warmup，再重复测量；至少报告 mean、median、std、p95。

### D006：安全主张
代码可验证正确性、消息篡改拒绝、重放窗口、密钥差异等可执行性质；不得据此声称完成 eCK 或 mBR 证明。

## C2LAKE 决策

### D101：矩阵 M 的形状
协议实现固定 `M ∈ Z_q^(n×n)`。  
理由：`d^T M`、`x^T M`、`M y`、`S^T M` 必须同时成立；论文前置定义中的 `m×n` 与协议正文冲突。

### D102：M 的秩
`paper_literal` 不强制 rank=m，只生成论文实验最可能使用的随机 n×n 矩阵。  
`audited` 记录实际模 q 秩；不声称满足论文“rank m”表述。

### D103：小向量采样
- `paper_literal`：严格按正文，只有明确写出范数界的向量采用 bounded sampler；`d_i1` 等未给界的量采用均匀 Zq。
- `audited_small_secret`：d、r_i、d_i1、x_i、y_i、z_i 均采用中心小分布或有界采样。
两类结果必须分开。

### D104：q 参数
论文实验表按 `q=m²`，即使它通常不是素数；这是 `paper_literal`。  
`audited_prime` 使用 `next_prime(m²)`。

### D105：n 参数
实验复现使用 `n=ceil(4m log2(m))`，与论文表 7 一致。

### D106：会话密钥输出
- literal：H3 映射为 `Z_q*` 标量；
- audited：同时导出 32 字节 KDF 输出，但保留 literal 标量用于对照。

### D107：Key_Agreement 计时口径
先分别测量 initiator、responder 和 full_handshake。原论文单列值口径不明，不擅自选择；报告中并列对照。

## LCLA-AKA 决策

### D201：维度口径
固定：
- A: n×m
- s1,s2,s: m
- f,pk,u1,u2: n
- X: n×m
- X^T: m×n
- E,C: m×m
- nA,nB,e,delta,m1,m2: m

### D202：pk 命名消歧
`pk_full = H1(ID) ∈ Z_q^n`。  
`u1,u2` 是公开分量，满足 `pk_full=u1+u2`。禁止将 tuple `(u1,u2)` 与向量 `pk_full` 使用同一变量名。

### D203：s2 的保密级别
按论文 literal，s2 可经公开信道发送并可公开存储；真正保密的用户贡献是 s1。代码命名使用 `kgc_share_s2`，避免误导。

### D204：q 冲突
论文使用 `q=2^24-1=16777215` 并称其为素数，但该值为合数。  
- paper profiles 保留该值；
- audited profiles 使用 `q=16777259`。

### D205：m/n 冲突
- `paper_correctness`: m=256,n=5；
- `paper_performance`: m=256,n=6；
- `audited_preserve_keylen`: m=256,n=5,q=下一素数；
- `audited_preserve_dimension`: m=288,n=6,q=下一素数。
不得把这些参数混为一个“论文参数”。

### D206：TrapGen/SamplePre 后端
先定义接口，不直接假定 Frodo 库提供 GPV TrapGen/SamplePre。  
后端分为：
- `real_trapdoor_backend`：真实 TrapGen/SamplePre；
- `constructed_key_backend`：先生成 s1,s2,f，再构造 pk，用于协议与性能分层测试；
- `toy_backend`：小参数性质测试。
constructed 模式不得用于声称复现静态密钥生成安全性。

### D207：H1 编程
在 constructed 模式下使用注册表/可编程 H1 将 ID 映射到已构造 pk；必须在结果中标注 `programmed_h1=true`。

### D208：H2 多用途
论文同一 H2 用作 MAC、KDF、身份掩码。实现必须使用域分离标签：
`LCLA-MAC-A`、`LCLA-MAC-B`、`LCLA-ID-MASK`、`LCLA-SESSION-KDF`。

### D209：身份编码
IDA/IDB 规范化为 UTF-8 字节，身份掩码输出长度等于编码后身份长度；不得假定自然恰好为 m 位。

### D210：reconciliation
按论文定义实现逐坐标 S()/Mod2()；随机位 b 必须成为 transcript 的一部分或由可复现 seed 生成并明确记录。

### D211：协议匿名性验证范围
仅验证 transcript 结构中首轮和次轮不直接出现身份，以及 Bob 能从 TA 恢复 IDA。不得把该结构测试表述为完整匿名性证明。
