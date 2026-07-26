# LCLA-AKA Definition 5 / Lemma 3 反例审计

本审计严格保留论文 literal 的 μ₀、μ₁、S 与 Mod2，不修改区间、噪声或模运算。
对每个小奇数 q 穷举 base、满足 `|e| < q/8-1` 的整数 e 和随机位 b，
比较 `a=base+2e (mod q)` 与 base 在同一公开 delta 下的 Mod2 输出。

| q | 素数 | 界内 e 数 | 违反 tuple 数 | 首个反例跨模边界 |
| ---: | :---: | ---: | ---: | :---: |
| 7 | True | 0 | 0 | - |
| 11 | True | 1 | 0 | - |
| 15 | False | 1 | 0 | - |
| 31 | True | 5 | 48 | True |
| 63 | False | 13 | 336 | True |
| 127 | True | 29 | 1680 | True |

- `definition5_literal_implemented=true`
- `lemma3_counterexample_found=True`
- `lemma3_universal_correctness=False`
- `paper_correctness_proof_supported=False`

只要任一素数 q 存在满足论文误差界的反例，便不能把 Lemma 3 当作已由
该 literal 实现支持的普遍正确性命题。非素数 q 的结果仅用于函数性质审计。
