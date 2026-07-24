# C2LAKE Core Validation Report

## Summary

- result: pass
- failed_cases: 0
- profiles: toy,paper_literal_m32,audited_prime_m32
- backend: safe,fast
- paper_manifest_sha256: 27502f8185258222a465750c124d1702b5a0bd387d8618f8f159b62258802e41
- protocol_key_agreement_implemented: false
- security_proof_verified: false

## Profile 100-seed validation

| profile | passed | failed | total |
| --- | ---: | ---: | ---: |
| audited_prime_m32 | 100 | 0 | 100 |
| paper_literal_m32 | 100 | 0 | 100 |
| toy | 100 | 0 | 100 |

## Safe/Fast Consistency

- passed: True

## Bounded Norm Checks

- passed: True
- checked_vectors: 104
- max_norm: 21.37755832643195

## Independent Formula Check

- passed: True

| profile | passed |
| --- | --- |
| audited_prime_m32 | True |
| paper_literal_m32 | True |
| toy | True |

## Negative Test Matrix

| tampered field | verification failed |
| --- | --- |
| ID | True |
| P | True |
| P_i0 | True |
| P_i1 | True |
| d_i0 | True |
