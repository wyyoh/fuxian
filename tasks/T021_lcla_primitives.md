# Task ID
T021

# Objective
实现 LCLA-AKA 的离散高斯、LWE 基础、S/Mod2 reconciliation、哈希域分离与 backend 接口。

# In scope
- centered representation
- Gaussian sampler
- signal/hint function
- Mod2
- TrapdoorBackend Protocol
- ConstructedKeyBackend
- ToyBackend
- 序列化与 H2 域分离

# Out of scope
- 完整三轮协议
- 对 LWE/ISIS 安全性的实验结论

# Acceptance criteria
1. S/Mod2 的逐坐标边界测试覆盖 q/4 邻域。
2. 在满足误差界的随机样本中 reconciliation 一致率达到测试设定的确定阈值。
3. constructed backend 明确输出 programmed_h1=true。
4. 同一 seed 完全复现。
5. 维度错误和模数错误被拒绝。
