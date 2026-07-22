# C2LAKE 算法冻结规格

## 类型

- q：模数。
- n：向量维度。
- M：n×n 矩阵，元素位于 Zq。
- 所有协议向量均按列向量存储；带 `^T M` 的结果为长度 n 的行向量，代码中仍用一维数组表示。

## Setup

输入：security parameter m、profile、seed。

1. 从 profile 获得 q、n、β。
2. 生成 M ∈ Zq^(n×n)。
3. 生成 master secret d ∈ Zq^n；literal 中按论文明确范数界采样。
4. 计算 P = d^T M mod q。
5. 初始化 H1/H2/H3。

输出：
- public params Δ=(n,q,β,M,P,hash suite)
- master secret d

## SetSecretValue(ID_i)

1. 生成 d_i1。
2. P_i1 = d_i1^T M mod q。
3. 返回 secret share d_i1 和 request (ID_i,P_i1)。

## PartialPrivateKeyExtract(ID_i,P_i1)

1. 生成 r_i。
2. P_i0 = r_i^T M mod q。
3. h1_i = H1(ID_i,P_i0,P_i1,P) ∈ Zq*。
4. d_i0 = r_i + h1_i d mod q。
5. 返回 (d_i0,P_i0)。

## VerifyAndAssembleKey

验证：

`d_i0^T M == P_i0 + H1(ID_i,P_i0,P_i1,P) P (mod q)`

成功后：

- private key sk_i=(d_i0,d_i1)
- public key pk_i=(P_i0,P_i1)

## InitiatorCreate

输入 Alice 长期密钥、peer ID、公参、timestamp。

1. 生成小向量 x_i,y_i,z_i。
2. X_i=x_i^T M。
3. Y_i=M y_i。
4. Z_i=M z_i。
5. h2_i=H2(ID_i,P_i0,P_i1,X_i,Y_i,Z_i,T_i)。
6. S_i=x_i+h2_i(d_i0+d_i1) mod q。
7. 输出 request transcript 和本地 ephemeral state。

## ResponderVerifyAndReply

验证时间窗口和：

`S_i^T M == X_i + h2_i(P_i0+P_i1+h1_i P) (mod q)`

成功后生成 Bob 的 x_j,y_j,z_j,X_j,Y_j,Z_j,S_j。

计算：

- k1 = X_i · y_j
- k2 = x_j^T · Y_i
- k3 = (P_i0+P_i1+h1_iP)·z_j + (d_j0+d_j1)^T·Z_i

全部 mod q。

session key：
`H3(P_i0,P_i1,X_i,Y_i,Z_i,P_j0,P_j1,X_j,Y_j,Z_j,k1,k2,k3)`

## InitiatorVerifyAndFinish

验证 Bob transcript。

计算：

- k1 = x_i^T · Y_j
- k2 = X_j · y_i
- k3 = (P_j0+P_j1+h1_jP)·z_i + (d_i0+d_i1)^T·Z_j

使用同一 canonical H3 字段顺序。

## 正确性不变量

- X_i y_j = x_i^T Y_j
- x_j^T Y_i = X_j y_i
- responder k3 = initiator k3
- SK_i = SK_j

## 错误处理

必须有稳定错误码：

- INVALID_TIMESTAMP
- INVALID_PARTIAL_KEY
- INVALID_INITIATOR_AUTH
- INVALID_RESPONDER_AUTH
- SHAPE_ERROR
- PROFILE_ERROR
