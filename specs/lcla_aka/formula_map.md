# LCLA-AKA 公式—代码—测试映射

| 论文位置 | 数学式 | 代码接口 | 测试 |
|---|---|---|---|
| Eq.(3) | u1=A s1+2f | `entity_keygen()` | shape、重算 |
| Eq.(4) | A s2=u2 | `sample_pre()` | 预像验证 |
| Static verify | A(s1+s2)+2f=pk | `verify_static_key()` | 正/负测试 |
| Alice request | C_A=X_A^T A+2E_A | `alice_request()` | shape、重算 |
| Alice request | n_A=X_A^T pk_B+2e_A | `alice_request()` | shape、保存 |
| Reconciliation | δ_A=S(n_A) | `signal()` | 坐标边界测试 |
| Reconciliation | m1=Mod2(n_A,δ_A) | `mod2()` | Lemma 3 性质测试 |
| Bob | n_A'=C_A s_B | `bob_respond()` | 误差差值与 m1 一致 |
| Bob | C_B=X_B^T A+2E_B | `bob_respond()` | shape、重算 |
| Alice | n_B'=C_B s_A+2e_B | `alice_finish()` | m2 一致 |
| Identity | T_A=ID_A xor mask | `mask_identity()` | 恢复完全一致 |
| Session | H2(ID_A,ID_B,m1,m2) | `derive_session_key()` | 双方一致 |
| Table IV | basic operation times | benchmark ops | raw CSV |
| Table V | protocol total times | benchmark protocol | raw CSV |
| Fig.4–6 | computation/communication scaling | plotting scripts | formula and measured modes |
