# 哈希与序列化规范

## 域分离

每个哈希调用必须具有固定 ASCII 标签，标签作为第一个字段。

## 字段编码

每个字段编码为：

`type_tag || uint64_be(length) || payload`

支持：

- bytes/string
- unsigned integer
- signed centered integer
- vector
- matrix
- timestamp
- identity

矩阵编码必须包含 rows、cols、q 和 row-major payload。

## SHAKE 输出

- 标量 Zq：读取足够字节，拒绝采样得到 [1,q-1]。
- bit vector：读取 ceil(m/8) 字节并截断。
- 会话 KDF：默认 32 字节。
- 身份掩码：输出恰好等于身份字节长度。

## 禁止事项

- 直接 `str(tuple)` 哈希；
- 无长度前缀拼接；
- 依赖 Python 对象 hash；
- 不同协议/用途复用同一标签。
