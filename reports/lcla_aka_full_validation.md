# LCLA-AKA Full Validation

- result: `partial_reproduction_observed_correctness_failure_constructed_backend_unverified_security`
- executable_validation_passed: `True`
- benchmark_status: `partial`
- backend_status: `partial_constructed_relation_only`
- accepted_session_consistency: `True`
- honest_execution_correctness_reproduced: `False`
- paper_correctness_claim_reproduced: `False`
- lemma3_universal_correctness: `False`
- honest_execution_attempts: `10000`
- honest_execution_accepted: `2498`
- formal_security_verified: `False`

`executable_validation_passed=true` 只表示状态机、constructed relation、条件接受
路径与篡改夹具可执行。它不表示诚实执行达到论文的高概率正确性主张。
无条件连续 seed 试验、目标误拒绝和 Lemma 3 素数 q 反例均独立保留。
