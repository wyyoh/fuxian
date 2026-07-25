# C2LAKE Theoretical Cost Reproduction

## Scope

- 仅重算 C2LAKE 自身的通信、存储和运算计数。
- `paper_compact_message_bytes` 按 Zq 元素最小位长估算，沿用论文忽略 ID/T 的紧凑口径。
- `canonical_hash_encoding_bytes` 是当前 SHAKE 输入的长度前缀编码长度。
- 当前项目未实现专用网络 wire serializer：`network_wire_encoding_defined=false`。
- canonical hash encoding 不应解释为实际网络通信开销，也不能直接用于否定或验证论文通信效率主张。
- 其他方案数据不在本报告中声称独立复现。
- 所有比特长度使用 `ceil(log2(q))` 或等价 `bit_length(q-1)`。

## Communication Cost

| profile | family | m | q | n | paper compact bytes | canonical hash encoding bytes | wire defined |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| audited_prime_m112 | audited_prime | 112 | 12547 | 3050 | 64050 | 293488 | False |
| audited_prime_m128 | audited_prime | 128 | 16411 | 3584 | 80640 | 344752 | False |
| audited_prime_m160 | audited_prime | 160 | 25601 | 4687 | 105458 | 450640 | False |
| audited_prime_m256 | audited_prime | 256 | 65537 | 8192 | 208896 | 787120 | False |
| audited_prime_m32 | audited_prime | 32 | 1031 | 640 | 10560 | 62128 | False |
| audited_prime_m48 | audited_prime | 48 | 2309 | 1073 | 19314 | 103696 | False |
| audited_prime_m64 | audited_prime | 64 | 4099 | 1536 | 29952 | 148144 | False |
| audited_prime_m80 | audited_prime | 80 | 6421 | 2024 | 39468 | 194992 | False |
| audited_prime_m96 | audited_prime | 96 | 9221 | 2529 | 53110 | 243472 | False |
| paper_literal_m112 | paper_literal | 112 | 12544 | 3050 | 64050 | 293488 | False |
| paper_literal_m128 | paper_literal | 128 | 16384 | 3584 | 75264 | 344752 | False |
| paper_literal_m160 | paper_literal | 160 | 25600 | 4687 | 105458 | 450640 | False |
| paper_literal_m256 | paper_literal | 256 | 65536 | 8192 | 196608 | 787120 | False |
| paper_literal_m32 | paper_literal | 32 | 1024 | 640 | 9600 | 62128 | False |
| paper_literal_m48 | paper_literal | 48 | 2304 | 1073 | 19314 | 103696 | False |
| paper_literal_m64 | paper_literal | 64 | 4096 | 1536 | 27648 | 148144 | False |
| paper_literal_m80 | paper_literal | 80 | 6400 | 2024 | 39468 | 194992 | False |
| paper_literal_m96 | paper_literal | 96 | 9216 | 2529 | 53110 | 243472 | False |
| toy | toy | 8 | 257 | 16 | 216 | 2224 | False |

## Storage Cost

| profile | item | math ideal bytes | NumPy int64 bytes | optimized estimate bytes |
| --- | --- | ---: | ---: | ---: |
| audited_prime_m112 | M | 16279375 | 74420000 | 18605000 |
| audited_prime_m112 | user_private_key_d_i0_d_i1 | 10675 | 48800 | 12200 |
| audited_prime_m112 | one_party_transcript_vectors | 32025 | 146400 | 36600 |
| audited_prime_m128 | M | 24084480 | 102760448 | 25690112 |
| audited_prime_m128 | user_private_key_d_i0_d_i1 | 13440 | 57344 | 14336 |
| audited_prime_m128 | one_party_transcript_vectors | 40320 | 172032 | 43008 |
| audited_prime_m160 | M | 41189942 | 175743752 | 43935938 |
| audited_prime_m160 | user_private_key_d_i0_d_i1 | 17577 | 74992 | 18748 |
| audited_prime_m160 | one_party_transcript_vectors | 52729 | 224976 | 56244 |
| audited_prime_m256 | M | 142606336 | 536870912 | 268435456 |
| audited_prime_m256 | user_private_key_d_i0_d_i1 | 34816 | 131072 | 65536 |
| audited_prime_m256 | one_party_transcript_vectors | 104448 | 393216 | 196608 |
| audited_prime_m32 | M | 563200 | 3276800 | 819200 |
| audited_prime_m32 | user_private_key_d_i0_d_i1 | 1760 | 10240 | 2560 |
| audited_prime_m32 | one_party_transcript_vectors | 5280 | 30720 | 7680 |
| audited_prime_m48 | M | 1726994 | 9210632 | 2302658 |
| audited_prime_m48 | user_private_key_d_i0_d_i1 | 3219 | 17168 | 4292 |
| audited_prime_m48 | one_party_transcript_vectors | 9657 | 51504 | 12876 |
| audited_prime_m64 | M | 3833856 | 18874368 | 4718592 |
| audited_prime_m64 | user_private_key_d_i0_d_i1 | 4992 | 24576 | 6144 |
| audited_prime_m64 | one_party_transcript_vectors | 14976 | 73728 | 18432 |
| audited_prime_m80 | M | 6656936 | 32772608 | 8193152 |
| audited_prime_m80 | user_private_key_d_i0_d_i1 | 6578 | 32384 | 8096 |
| audited_prime_m80 | one_party_transcript_vectors | 19734 | 97152 | 24288 |
| audited_prime_m96 | M | 11192722 | 51166728 | 12791682 |
| audited_prime_m96 | user_private_key_d_i0_d_i1 | 8852 | 40464 | 10116 |
| audited_prime_m96 | one_party_transcript_vectors | 26555 | 121392 | 30348 |
| paper_literal_m112 | M | 16279375 | 74420000 | 18605000 |
| paper_literal_m112 | user_private_key_d_i0_d_i1 | 10675 | 48800 | 12200 |
| paper_literal_m112 | one_party_transcript_vectors | 32025 | 146400 | 36600 |
| paper_literal_m128 | M | 22478848 | 102760448 | 25690112 |
| paper_literal_m128 | user_private_key_d_i0_d_i1 | 12544 | 57344 | 14336 |
| paper_literal_m128 | one_party_transcript_vectors | 37632 | 172032 | 43008 |
| paper_literal_m160 | M | 41189942 | 175743752 | 43935938 |
| paper_literal_m160 | user_private_key_d_i0_d_i1 | 17577 | 74992 | 18748 |
| paper_literal_m160 | one_party_transcript_vectors | 52729 | 224976 | 56244 |
| paper_literal_m256 | M | 134217728 | 536870912 | 134217728 |
| paper_literal_m256 | user_private_key_d_i0_d_i1 | 32768 | 131072 | 32768 |
| paper_literal_m256 | one_party_transcript_vectors | 98304 | 393216 | 98304 |
| paper_literal_m32 | M | 512000 | 3276800 | 819200 |
| paper_literal_m32 | user_private_key_d_i0_d_i1 | 1600 | 10240 | 2560 |
| paper_literal_m32 | one_party_transcript_vectors | 4800 | 30720 | 7680 |
| paper_literal_m48 | M | 1726994 | 9210632 | 2302658 |
| paper_literal_m48 | user_private_key_d_i0_d_i1 | 3219 | 17168 | 4292 |
| paper_literal_m48 | one_party_transcript_vectors | 9657 | 51504 | 12876 |
| paper_literal_m64 | M | 3538944 | 18874368 | 4718592 |
| paper_literal_m64 | user_private_key_d_i0_d_i1 | 4608 | 24576 | 6144 |
| paper_literal_m64 | one_party_transcript_vectors | 13824 | 73728 | 18432 |
| paper_literal_m80 | M | 6656936 | 32772608 | 8193152 |
| paper_literal_m80 | user_private_key_d_i0_d_i1 | 6578 | 32384 | 8096 |
| paper_literal_m80 | one_party_transcript_vectors | 19734 | 97152 | 24288 |
| paper_literal_m96 | M | 11192722 | 51166728 | 12791682 |
| paper_literal_m96 | user_private_key_d_i0_d_i1 | 8852 | 40464 | 10116 |
| paper_literal_m96 | one_party_transcript_vectors | 26555 | 121392 | 30348 |
| toy | M | 288 | 2048 | 512 |
| toy | master_secret_d | 18 | 128 | 32 |
| toy | master_public_P | 18 | 128 | 32 |
| toy | user_private_key_d_i0_d_i1 | 36 | 256 | 64 |
| toy | user_public_key_P_i0_P_i1 | 36 | 256 | 64 |
| toy | ephemeral_state_x_y_z | 54 | 384 | 96 |
| toy | one_party_transcript_vectors | 108 | 768 | 192 |

## Operation Counts

| profile | phase | v×M | M×v | dot | add | scalar×v | H1 | H2 | H3 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| audited_prime_m32 | Setup | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| audited_prime_m32 | SetSecretValue | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| audited_prime_m32 | PartialPrivateKeyExtract | 1 | 0 | 0 | 1 | 1 | 1 | 0 | 0 |
| audited_prime_m32 | initiator_create | 1 | 2 | 0 | 2 | 1 | 0 | 1 | 0 |
| audited_prime_m32 | responder_verify_and_reply | 2 | 2 | 4 | 7 | 3 | 1 | 2 | 1 |
| audited_prime_m32 | initiator_verify_and_finish | 1 | 0 | 4 | 4 | 2 | 1 | 1 | 1 |
| audited_prime_m32 | full_handshake | 7 | 4 | 8 | 14 | 7 | 3 | 4 | 2 |
| paper_literal_m32 | Setup | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| paper_literal_m32 | SetSecretValue | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| paper_literal_m32 | PartialPrivateKeyExtract | 1 | 0 | 0 | 1 | 1 | 1 | 0 | 0 |
| paper_literal_m32 | initiator_create | 1 | 2 | 0 | 2 | 1 | 0 | 1 | 0 |
| paper_literal_m32 | responder_verify_and_reply | 2 | 2 | 4 | 7 | 3 | 1 | 2 | 1 |
| paper_literal_m32 | initiator_verify_and_finish | 1 | 0 | 4 | 4 | 2 | 1 | 1 | 1 |
| paper_literal_m32 | full_handshake | 7 | 4 | 8 | 14 | 7 | 3 | 4 | 2 |
| toy | Setup | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| toy | SetSecretValue | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| toy | PartialPrivateKeyExtract | 1 | 0 | 0 | 1 | 1 | 1 | 0 | 0 |
| toy | initiator_create | 1 | 2 | 0 | 2 | 1 | 0 | 1 | 0 |
| toy | responder_verify_and_reply | 2 | 2 | 4 | 7 | 3 | 1 | 2 | 1 |
| toy | initiator_verify_and_finish | 1 | 0 | 4 | 4 | 2 | 1 | 1 | 1 |
| toy | full_handshake | 7 | 4 | 8 | 14 | 7 | 3 | 4 | 2 |
