# C2LAKE Table 7 / Figure 4 Benchmark Report

## Summary

- mode: smoke
- completed_profiles: audited_prime_m32, paper_literal_m32, toy
- incomplete_profiles: none
- Key_Agreement timing boundary is ambiguous in the paper; initiator_total, responder_total and full_handshake are reported separately.
- Raw benchmark rows are never overwritten; reruns require --resume.

## Reproduced Table 7 Statistics

| profile | phase | samples | failed | mean_ms | median_ms | cv |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| audited_prime_m32 | PartialPrivateKeyExtract | 1 | 0 | 9.704499 | 9.704499 | 0.0 |
| audited_prime_m32 | SetSecretValue | 1 | 0 | 2.050784 | 2.050784 | 0.0 |
| audited_prime_m32 | Setup | 1 | 0 | 17.618639 | 17.618639 | 0.0 |
| audited_prime_m32 | full_handshake | 1 | 0 | 66.1528 | 66.1528 | 0.0 |
| audited_prime_m32 | initiator_total | 1 | 0 | 25.473608 | 25.473608 | 0.0 |
| audited_prime_m32 | responder_total | 1 | 0 | 28.142652 | 28.142652 | 0.0 |
| paper_literal_m32 | PartialPrivateKeyExtract | 1 | 0 | 3.846238 | 3.846238 | 0.0 |
| paper_literal_m32 | SetSecretValue | 1 | 0 | 2.056749 | 2.056749 | 0.0 |
| paper_literal_m32 | Setup | 1 | 0 | 16.878697 | 16.878697 | 0.0 |
| paper_literal_m32 | full_handshake | 1 | 0 | 66.980016 | 66.980016 | 0.0 |
| paper_literal_m32 | initiator_total | 1 | 0 | 23.494104 | 23.494104 | 0.0 |
| paper_literal_m32 | responder_total | 1 | 0 | 23.024529 | 23.024529 | 0.0 |
| toy | PartialPrivateKeyExtract | 1 | 0 | 0.536105 | 0.536105 | 0.0 |
| toy | SetSecretValue | 1 | 0 | 0.186379 | 0.186379 | 0.0 |
| toy | Setup | 1 | 0 | 11.615421 | 11.615421 | 0.0 |
| toy | full_handshake | 1 | 0 | 7.854389 | 7.854389 | 0.0 |
| toy | initiator_total | 1 | 0 | 9.23445 | 9.23445 | 0.0 |
| toy | responder_total | 1 | 0 | 7.104103 | 7.104103 | 0.0 |

## Paper Comparison

| m | phase | boundary | paper_ms | reproduced_mean_ms | rel_error_% | trend_match |
| ---: | --- | --- | ---: | ---: | ---: | --- |
| 32 | Setup | setup | 2.867 | 16.878697 | 488.72329961632363 | insufficient_data |
| 32 | SetSecretValue | set_secret_value | 0.578 | 2.056749 | 255.83892733564016 | insufficient_data |
| 32 | PartialPrivateKeyExtract | partial_private_key_extract | 0.59 | 3.846238 | 551.9047457627119 | insufficient_data |
| 32 | Key_Agreement | initiator_total | 1.315 | 23.494104 | 1686.623878326996 | insufficient_data |
| 32 | Key_Agreement | responder_total | 1.315 | 23.024529 | 1650.9147528517112 | insufficient_data |
| 32 | Key_Agreement | full_handshake | 1.315 | 66.980016 | 4993.537338403043 | insufficient_data |
| 48 | Setup | setup | 6.493 |  |  | incomplete |
| 48 | SetSecretValue | set_secret_value | 1.649 |  |  | incomplete |
| 48 | PartialPrivateKeyExtract | partial_private_key_extract | 1.599 |  |  | incomplete |
| 48 | Key_Agreement | initiator_total | 3.465 |  |  | incomplete |
| 48 | Key_Agreement | responder_total | 3.465 |  |  | incomplete |
| 48 | Key_Agreement | full_handshake | 3.465 |  |  | incomplete |
| 64 | Setup | setup | 18.855 |  |  | incomplete |
| 64 | SetSecretValue | set_secret_value | 6.138 |  |  | incomplete |
| 64 | PartialPrivateKeyExtract | partial_private_key_extract | 6.166 |  |  | incomplete |
| 64 | Key_Agreement | initiator_total | 10.201 |  |  | incomplete |
| 64 | Key_Agreement | responder_total | 10.201 |  |  | incomplete |
| 64 | Key_Agreement | full_handshake | 10.201 |  |  | incomplete |
| 80 | Setup | setup | 60.554 |  |  | incomplete |
| 80 | SetSecretValue | set_secret_value | 18.433 |  |  | incomplete |
| 80 | PartialPrivateKeyExtract | partial_private_key_extract | 18.439 |  |  | incomplete |
| 80 | Key_Agreement | initiator_total | 26.162 |  |  | incomplete |
| 80 | Key_Agreement | responder_total | 26.162 |  |  | incomplete |
| 80 | Key_Agreement | full_handshake | 26.162 |  |  | incomplete |
| 96 | Setup | setup | 93.497 |  |  | incomplete |
| 96 | SetSecretValue | set_secret_value | 29.546 |  |  | incomplete |
| 96 | PartialPrivateKeyExtract | partial_private_key_extract | 29.583 |  |  | incomplete |
| 96 | Key_Agreement | initiator_total | 40.601 |  |  | incomplete |
| 96 | Key_Agreement | responder_total | 40.601 |  |  | incomplete |
| 96 | Key_Agreement | full_handshake | 40.601 |  |  | incomplete |
| 112 | Setup | setup | 133.434 |  |  | incomplete |
| 112 | SetSecretValue | set_secret_value | 42.687 |  |  | incomplete |
| 112 | PartialPrivateKeyExtract | partial_private_key_extract | 42.824 |  |  | incomplete |
| 112 | Key_Agreement | initiator_total | 57.668 |  |  | incomplete |
| 112 | Key_Agreement | responder_total | 57.668 |  |  | incomplete |
| 112 | Key_Agreement | full_handshake | 57.668 |  |  | incomplete |
| 128 | Setup | setup | 143.566 |  |  | incomplete |
| 128 | SetSecretValue | set_secret_value | 82.891 |  |  | incomplete |
| 128 | PartialPrivateKeyExtract | partial_private_key_extract | 82.919 |  |  | incomplete |
| 128 | Key_Agreement | initiator_total | 103.428 |  |  | incomplete |
| 128 | Key_Agreement | responder_total | 103.428 |  |  | incomplete |
| 128 | Key_Agreement | full_handshake | 103.428 |  |  | incomplete |
| 160 | Setup | setup | 357.661 |  |  | incomplete |
| 160 | SetSecretValue | set_secret_value | 127.983 |  |  | incomplete |
| 160 | PartialPrivateKeyExtract | partial_private_key_extract | 126.65 |  |  | incomplete |
| 160 | Key_Agreement | initiator_total | 167.743 |  |  | incomplete |
| 160 | Key_Agreement | responder_total | 167.743 |  |  | incomplete |
| 160 | Key_Agreement | full_handshake | 167.743 |  |  | incomplete |
| 256 | Setup | setup | 976.411 |  |  | incomplete |
| 256 | SetSecretValue | set_secret_value | 632.302 |  |  | incomplete |
| 256 | PartialPrivateKeyExtract | partial_private_key_extract | 631.12 |  |  | incomplete |
| 256 | Key_Agreement | initiator_total | 747.21 |  |  | incomplete |
| 256 | Key_Agreement | responder_total | 747.21 |  |  | incomplete |
| 256 | Key_Agreement | full_handshake | 747.21 |  |  | incomplete |
