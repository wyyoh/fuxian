# LCLA-AKA 算法冻结规格

## 固定维度

- A ∈ Zq^(n×m)
- s1,s2,s ∈ Zq^m
- f,pk_full,u1,u2 ∈ Zq^n
- X ∈ Zq^(n×m), X^T ∈ Zq^(m×n)
- E,C ∈ Zq^(m×m)
- e,nA,nB ∈ Zq^m
- delta,m1,m2 ∈ {0,1}^m

## Setup

1. 根据 backend 调用 `TrapGen(n,m,q)`，获得 A 和 trapdoor。
2. 初始化 H1: ID→Zq^n。
3. 初始化域分离 H2 suite。

## EntityKeyGeneration

1. 采样 s1 ∈ Zq^m。
2. 采样 f ← χ_beta^n。
3. u1=A s1+2f mod q。
4. pk_full=H1(ID)。
5. 发送 (ID,u1,pk_full) 给 KGC；正文有时省略 ID，工程接口必须显式绑定。

## KGCKeyGeneration

1. u2=pk_full-u1 mod q。
2. s2=SamplePre(A,trapdoor,beta,u2)，要求 A s2=u2 mod q。
3. 通过公开信道返回 s2。

## EntityVerify

验证：
`A(s1+s2)+2f == pk_full (mod q)`

保存：
- secret contribution s1
- public KGC share s2
- combined static secret s=s1+s2
- public components u1,u2
- deterministic pk_full

## AliceRequest

1. Alice 已知 ID_B，计算 pk_B=H1(ID_B)。
2. 采样 X_A、E_A、e_A。
3. C_A=X_A^T A+2E_A。
4. n_A=X_A^T pk_B+2e_A。
5. delta_A=S(n_A)。
6. m_A1=Mod2(n_A,delta_A)。
7. h_A=H2[LCLA-MAC-A](C_A,m_A1,delta_A)。
8. 广播 (C_A,delta_A,h_A)。

## BobResponse

1. n_A'=C_A s_B。
2. m_B1=Mod2(n_A',delta_A)。
3. 验证 h_A。
4. 采样 X_B,E_B。
5. C_B=X_B^T A+2E_B。
6. h_B=H2[LCLA-MAC-B](C_B,m_B1)。
7. 广播 (C_B,h_B)。

## AliceFinish

1. 验证 h_B。
2. 采样 e_B。
3. n_B'=C_B s_A+2e_B。
4. delta_B=S(n_B')。
5. m_A2=Mod2(n_B',delta_B)。
6. mask=H2[LCLA-ID-MASK](delta_B,h_A,C_B,m_A1)，长度等于 ID_A 字节长度。
7. T_A=ID_A_bytes XOR mask。
8. SK_A=H2[LCLA-SESSION-KDF](ID_A,ID_B,m_A1,m_A2)。
9. 广播 (T_A,delta_B)。

## BobFinish

1. 使用同一 mask 恢复 ID_A。
2. pk_A=H1(ID_A)。
3. n_B=X_B^T pk_A。
4. m_B2=Mod2(n_B,delta_B)。
5. SK_B=H2[LCLA-SESSION-KDF](ID_A,ID_B,m_B1,m_B2)。

## 正确性目标

- m_A1=m_B1
- m_A2=m_B2
- SK_A=SK_B

## 后端分层

### real_trapdoor_backend
真实 TrapGen/SamplePre；可用于静态密钥生成复现。

### constructed_key_backend
先生成 s1,s2,f，再令 pk_full=A(s1+s2)+2f，并将 H1(ID) 注册为该值。  
仅用于协议层与 benchmark 分层；必须标注 programmed_h1。

### toy_backend
小参数、确定性、用于单元测试与性质测试。

## 稳定错误码

- H1_BINDING_ERROR
- PREIMAGE_ERROR
- STATIC_KEY_VERIFY_ERROR
- NOT_INTENDED_RECEIVER
- INVALID_RESPONDER_MAC
- RECONCILIATION_FAILURE
- ID_RECOVERY_FAILURE
- SHAPE_ERROR
- PROFILE_ERROR
