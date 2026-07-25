# LCLA-AKA reconciliation 冻结规格

来源：原论文文件第 4 页、印刷页 9216，Definition 5；Lemma 3 位于同页。

## Centered 口径

`r ∈ Zq` 先解释为 centered representative。令 `a=floor(q/4)`：

- `mu_0(r)=0` 当且仅当 `r ∈ [-a,a]`，否则为 1；
- `mu_1(r)=0` 当且仅当 `r ∈ [-a+1,a+1]`，否则为 1。

论文公式使用闭区间。实现保留两个端点，未将其改成半开区间。

## Hint

对每个坐标独立选择 `b <- {0,1}`，并计算：

```text
S(x) = mu_b(x)
```

实际发送的是完整 `delta=S(x)`。本地随机 `b` 只用于生成 delta，不需要额外发送。
实验使用显式 seed 的 PCG64 以保证可复现；这不是生产级 CSPRNG。

## Robust extractor

```text
Mod2(x, delta) =
    ((x + delta*((q-1)//2)) mod q) mod 2
```

要求 `q` 为奇数且 `q>2`。

## Lemma 3 检查边界

论文给出：若 `a=b+2e` 且 `||e|| < q/8 - 1`，则应有：

```text
Mod2(a,S(a)) = Mod2(b,S(a))
```

项目以穷举小参数、临界点和性质测试检查该关系。超出界时允许不一致，统计但不
删除失败样本。该可执行检查不等同于对论文安全证明的形式化验证。
