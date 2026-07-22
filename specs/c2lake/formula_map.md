# C2LAKE 公式—代码—测试映射

| 论文位置 | 数学式 | 代码接口 | 核心测试 |
|---|---|---|---|
| Setup | P=d^T M mod q | `setup()` | shape、范围、固定 seed |
| 5.2 | P_i1=d_i1^T M | `set_secret_value()` | 直接重算 |
| 5.3 | P_i0=r_i^T M | `extract_partial_key()` | 直接重算 |
| 5.3 | d_i0=r_i+h1_i d | `extract_partial_key()` | 私钥验证 |
| 5.4 | d_i0^T M=P_i0+h1_iP | `verify_partial_key()` | 100/100 随机通过 |
| 5.5 | X_i=x_i^T M | `create_message()` | shape与重算 |
| 5.5 | Y_i=M y_i | `create_message()` | shape与重算 |
| 5.5 | Z_i=M z_i | `create_message()` | shape与重算 |
| 5.5 | S_i=x_i+h2_i(d_i0+d_i1) | `create_message()` | 验证式通过 |
| Eq.(6) | S_i^T M=X_i+h2_i(P_i0+P_i1+h1_iP) | `verify_message()` | 篡改单字段失败 |
| Theorem 1 | K1/K2/K3 双方一致 | `derive_components()` | property test |
| H3 | transcript+K1+K2+K3 | `derive_session_key()` | 双方 key 相同 |
| Table 7 | 四阶段运行时间 | benchmark scripts | CSV、统计、论文对比 |
