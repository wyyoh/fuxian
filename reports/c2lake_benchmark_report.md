# C2LAKE Table 7 / Figure 4 Benchmark Report

## Summary

- mode: exact
- completed_profiles: audited_prime_m112, audited_prime_m128, audited_prime_m160, audited_prime_m32, audited_prime_m48, audited_prime_m64, audited_prime_m80, audited_prime_m96, paper_literal_m112, paper_literal_m128, paper_literal_m160, paper_literal_m32, paper_literal_m48, paper_literal_m64, paper_literal_m80, paper_literal_m96
- incomplete_profiles: audited_prime_m256, paper_literal_m256
- Key_Agreement timing boundary is ambiguous in the paper; initiator_total, responder_total and full_handshake are reported separately.
- Raw benchmark rows are never overwritten; reruns require --resume.

## Reproduced Table 7 Statistics

| profile | phase | samples | failed | mean_ms | median_ms | cv |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| audited_prime_m112 | PartialPrivateKeyExtract | 100 | 0 | 55.6983057 | 54.103900499999995 | 0.11625314977557528 |
| audited_prime_m112 | SetSecretValue | 100 | 0 | 54.87216281 | 52.7556515 | 0.1291599391116142 |
| audited_prime_m112 | Setup | 100 | 0 | 128.1689626 | 124.29874699999999 | 0.10087039695066231 |
| audited_prime_m112 | full_handshake | 100 | 0 | 403.06391169 | 396.41139499999997 | 0.0764567160681852 |
| audited_prime_m112 | initiator_total | 100 | 0 | 200.38003313000002 | 198.278017 | 0.06267310758304176 |
| audited_prime_m112 | responder_total | 100 | 0 | 197.81460854 | 196.516276 | 0.04822836222943735 |
| audited_prime_m128 | PartialPrivateKeyExtract | 100 | 0 | 146.89097579 | 146.189843 | 0.03765222848896938 |
| audited_prime_m128 | SetSecretValue | 100 | 0 | 146.15732636 | 143.7320325 | 0.05964946922443329 |
| audited_prime_m128 | Setup | 100 | 0 | 242.44363130999997 | 239.763893 | 0.048458251831692674 |
| audited_prime_m128 | full_handshake | 100 | 0 | 813.68556217 | 807.1324775 | 0.0403949782508448 |
| audited_prime_m128 | initiator_total | 100 | 0 | 410.34432838 | 402.356476 | 0.1115514515364518 |
| audited_prime_m128 | responder_total | 100 | 0 | 408.72779681 | 402.094912 | 0.09791089789305778 |
| audited_prime_m160 | PartialPrivateKeyExtract | 100 | 0 | 154.85195557 | 152.29349200000001 | 0.054040824284915544 |
| audited_prime_m160 | SetSecretValue | 100 | 0 | 155.0794148 | 152.61065 | 0.06445452374224596 |
| audited_prime_m160 | Setup | 100 | 0 | 323.13763458 | 318.790751 | 0.04223313146776117 |
| audited_prime_m160 | full_handshake | 100 | 0 | 1067.43326306 | 1045.227577 | 0.051811526621115184 |
| audited_prime_m160 | initiator_total | 100 | 0 | 529.3171891000001 | 524.2235415 | 0.03764981616015723 |
| audited_prime_m160 | responder_total | 100 | 0 | 530.77903407 | 521.8685204999999 | 0.05346170401238124 |
| audited_prime_m256 | PartialPrivateKeyExtract | 0 | 100 |  |  |  |
| audited_prime_m256 | SetSecretValue | 0 | 100 |  |  |  |
| audited_prime_m256 | Setup | 0 | 100 |  |  |  |
| audited_prime_m256 | full_handshake | 0 | 100 |  |  |  |
| audited_prime_m256 | initiator_total | 0 | 100 |  |  |  |
| audited_prime_m256 | responder_total | 0 | 100 |  |  |  |
| audited_prime_m32 | PartialPrivateKeyExtract | 100 | 0 | 4.2662172 | 3.436998 | 0.6160952119298512 |
| audited_prime_m32 | SetSecretValue | 100 | 0 | 2.27834302 | 2.2088875000000003 | 0.15391113634420697 |
| audited_prime_m32 | Setup | 100 | 0 | 13.344833020000001 | 12.909122 | 0.14440147774260886 |
| audited_prime_m32 | full_handshake | 100 | 0 | 60.03650449 | 56.127342 | 0.348066481887163 |
| audited_prime_m32 | initiator_total | 100 | 0 | 25.76881834 | 24.84422 | 0.36394604325015983 |
| audited_prime_m32 | responder_total | 100 | 0 | 26.84286617 | 26.521274 | 0.33288468029165535 |
| audited_prime_m48 | PartialPrivateKeyExtract | 100 | 0 | 8.4508457 | 7.965766 | 0.21551155450505052 |
| audited_prime_m48 | SetSecretValue | 100 | 0 | 8.10316025 | 8.0630955 | 0.0932692425387877 |
| audited_prime_m48 | Setup | 100 | 0 | 23.04416807 | 22.641045 | 0.06995099236810517 |
| audited_prime_m48 | full_handshake | 100 | 0 | 81.32577877 | 77.94582650000001 | 0.20964549013016234 |
| audited_prime_m48 | initiator_total | 100 | 0 | 39.18467071 | 37.000346500000006 | 0.1982058654560451 |
| audited_prime_m48 | responder_total | 100 | 0 | 38.72153757 | 36.7340795 | 0.20227243202720208 |
| audited_prime_m64 | PartialPrivateKeyExtract | 100 | 0 | 15.39574983 | 14.8367585 | 0.13011627979382281 |
| audited_prime_m64 | SetSecretValue | 100 | 0 | 16.26097638 | 15.989355 | 0.07904925638842845 |
| audited_prime_m64 | Setup | 100 | 0 | 39.19939175 | 38.671461 | 0.08475224312172937 |
| audited_prime_m64 | full_handshake | 100 | 0 | 123.62976208 | 119.469882 | 0.1075098175973157 |
| audited_prime_m64 | initiator_total | 100 | 0 | 62.072678960000005 | 61.4195225 | 0.10681522786963192 |
| audited_prime_m64 | responder_total | 100 | 0 | 61.24774424 | 60.572542999999996 | 0.10116439313717349 |
| audited_prime_m80 | PartialPrivateKeyExtract | 100 | 0 | 21.63778475 | 21.1112775 | 0.11649789849916173 |
| audited_prime_m80 | SetSecretValue | 100 | 0 | 23.68968405 | 23.200543 | 0.08638092571642947 |
| audited_prime_m80 | Setup | 100 | 0 | 57.181030549999996 | 56.212132 | 0.07907232427095898 |
| audited_prime_m80 | full_handshake | 100 | 0 | 173.08101645 | 170.2115435 | 0.08817797808840437 |
| audited_prime_m80 | initiator_total | 100 | 0 | 86.44562549 | 84.2233045 | 0.14959398485881537 |
| audited_prime_m80 | responder_total | 100 | 0 | 86.06569958 | 83.808517 | 0.11641404637313592 |
| audited_prime_m96 | PartialPrivateKeyExtract | 100 | 0 | 45.62944391 | 45.046328 | 0.08629441148198765 |
| audited_prime_m96 | SetSecretValue | 100 | 0 | 44.31030957 | 43.9301895 | 0.08195844008281487 |
| audited_prime_m96 | Setup | 100 | 0 | 98.57359993 | 98.08087549999999 | 0.05827306707347323 |
| audited_prime_m96 | full_handshake | 100 | 0 | 325.67183655 | 322.507745 | 0.07978675120961302 |
| audited_prime_m96 | initiator_total | 100 | 0 | 162.11207682 | 162.03738650000003 | 0.05275081626064549 |
| audited_prime_m96 | responder_total | 100 | 0 | 162.64198966 | 161.5605165 | 0.0655286404092179 |
| paper_literal_m112 | PartialPrivateKeyExtract | 100 | 0 | 57.21403719 | 56.0827055 | 0.10325299693345732 |
| paper_literal_m112 | SetSecretValue | 100 | 0 | 55.97473846 | 55.5909305 | 0.0699175626188556 |
| paper_literal_m112 | Setup | 100 | 0 | 128.73357796 | 126.064924 | 0.060992034889291974 |
| paper_literal_m112 | full_handshake | 100 | 0 | 413.90568933000003 | 402.46394499999997 | 0.06817582679168593 |
| paper_literal_m112 | initiator_total | 100 | 0 | 208.04427393000003 | 204.167296 | 0.0750976474693431 |
| paper_literal_m112 | responder_total | 100 | 0 | 208.25571779 | 202.9119685 | 0.07479044671521591 |
| paper_literal_m128 | PartialPrivateKeyExtract | 100 | 0 | 154.97371241000002 | 151.753082 | 0.06611110621410612 |
| paper_literal_m128 | SetSecretValue | 100 | 0 | 153.68091235 | 150.6806195 | 0.0697236468438662 |
| paper_literal_m128 | Setup | 100 | 0 | 251.64869851 | 245.222664 | 0.08326041529605523 |
| paper_literal_m128 | full_handshake | 100 | 0 | 873.54125545 | 853.1357204999999 | 0.08182892607823422 |
| paper_literal_m128 | initiator_total | 100 | 0 | 433.69871221 | 423.7298295 | 0.07208703772590619 |
| paper_literal_m128 | responder_total | 100 | 0 | 433.2364476 | 423.81196750000004 | 0.06984079652802898 |
| paper_literal_m160 | PartialPrivateKeyExtract | 100 | 0 | 143.13736795 | 131.381164 | 0.15473369545777627 |
| paper_literal_m160 | SetSecretValue | 100 | 0 | 142.30252889 | 129.918593 | 0.15515471800066755 |
| paper_literal_m160 | Setup | 100 | 0 | 304.65501474 | 279.118789 | 0.1390977926721671 |
| paper_literal_m160 | full_handshake | 100 | 0 | 986.99783702 | 892.3930359999999 | 0.15701024996553123 |
| paper_literal_m160 | initiator_total | 100 | 0 | 493.33954689999996 | 447.37591999999995 | 0.16355052652499422 |
| paper_literal_m160 | responder_total | 100 | 0 | 492.92618016 | 446.02332049999995 | 0.1559284101175265 |
| paper_literal_m256 | PartialPrivateKeyExtract | 0 | 100 |  |  |  |
| paper_literal_m256 | SetSecretValue | 0 | 100 |  |  |  |
| paper_literal_m256 | Setup | 0 | 100 |  |  |  |
| paper_literal_m256 | full_handshake | 0 | 100 |  |  |  |
| paper_literal_m256 | initiator_total | 0 | 100 |  |  |  |
| paper_literal_m256 | responder_total | 0 | 100 |  |  |  |
| paper_literal_m32 | PartialPrivateKeyExtract | 100 | 0 | 4.67260473 | 4.115726 | 0.42503266324303524 |
| paper_literal_m32 | SetSecretValue | 100 | 0 | 1.35890593 | 1.289529 | 0.17425347481253092 |
| paper_literal_m32 | Setup | 100 | 0 | 12.95519384 | 12.6785485 | 0.1319491259879744 |
| paper_literal_m32 | full_handshake | 100 | 0 | 54.92948689 | 52.5935675 | 0.3210633414333379 |
| paper_literal_m32 | initiator_total | 100 | 0 | 28.241279759999998 | 26.252524 | 0.33821920731393673 |
| paper_literal_m32 | responder_total | 100 | 0 | 27.70667401 | 25.0938545 | 0.340436678669509 |
| paper_literal_m48 | PartialPrivateKeyExtract | 100 | 0 | 9.69252567 | 9.386334999999999 | 0.15760870825020531 |
| paper_literal_m48 | SetSecretValue | 100 | 0 | 6.57879598 | 6.420082 | 0.1542183208313438 |
| paper_literal_m48 | Setup | 100 | 0 | 23.766447600000003 | 23.3956425 | 0.08735301143690778 |
| paper_literal_m48 | full_handshake | 100 | 0 | 80.17881371 | 77.15462450000001 | 0.19995987138789395 |
| paper_literal_m48 | initiator_total | 100 | 0 | 39.47241634 | 38.468380999999994 | 0.18726328827199176 |
| paper_literal_m48 | responder_total | 100 | 0 | 38.940915759999996 | 38.7094685 | 0.17553234525459452 |
| paper_literal_m64 | PartialPrivateKeyExtract | 100 | 0 | 16.52173353 | 16.282733999999998 | 0.0827798951167725 |
| paper_literal_m64 | SetSecretValue | 100 | 0 | 13.04332003 | 12.877720499999999 | 0.05883358135118052 |
| paper_literal_m64 | Setup | 100 | 0 | 37.687338260000004 | 37.3093555 | 0.05304304396524339 |
| paper_literal_m64 | full_handshake | 100 | 0 | 117.37975708 | 114.484123 | 0.10616590973201623 |
| paper_literal_m64 | initiator_total | 100 | 0 | 59.515000060000006 | 58.3592185 | 0.1182633328279061 |
| paper_literal_m64 | responder_total | 100 | 0 | 60.19159785 | 57.8669605 | 0.1276849377558187 |
| paper_literal_m80 | PartialPrivateKeyExtract | 100 | 0 | 25.295160139999997 | 25.121995 | 0.06739147507199446 |
| paper_literal_m80 | SetSecretValue | 100 | 0 | 20.10850144 | 19.584381999999998 | 0.11209996853656844 |
| paper_literal_m80 | Setup | 100 | 0 | 56.36473422 | 55.8973825 | 0.04123629972138767 |
| paper_literal_m80 | full_handshake | 100 | 0 | 170.18059669 | 168.4345835 | 0.06568175514489825 |
| paper_literal_m80 | initiator_total | 100 | 0 | 85.42247534 | 84.611699 | 0.07736299521333753 |
| paper_literal_m80 | responder_total | 100 | 0 | 85.32971760000001 | 84.280486 | 0.06757247935931421 |
| paper_literal_m96 | PartialPrivateKeyExtract | 100 | 0 | 45.41760913 | 44.951811 | 0.04134445832645251 |
| paper_literal_m96 | SetSecretValue | 100 | 0 | 44.32433234 | 44.0482095 | 0.04186335459937338 |
| paper_literal_m96 | Setup | 100 | 0 | 99.27604515000002 | 98.83216999999999 | 0.03248664515959444 |
| paper_literal_m96 | full_handshake | 100 | 0 | 326.77540051 | 324.4660675 | 0.03288674744858898 |
| paper_literal_m96 | initiator_total | 100 | 0 | 163.24486184 | 162.4620765 | 0.0358300369262534 |
| paper_literal_m96 | responder_total | 100 | 0 | 163.42908552999998 | 162.566611 | 0.040985728538944215 |

## Paper Comparison

| m | phase | boundary | paper_ms | reproduced_mean_ms | rel_error_% | trend_match |
| ---: | --- | --- | ---: | ---: | ---: | --- |
| 32 | Setup | setup | 2.867 | 12.95519384 | 351.8728231600976 | True |
| 32 | SetSecretValue | set_secret_value | 0.578 | 1.35890593 | 135.10483217993078 | False |
| 32 | PartialPrivateKeyExtract | partial_private_key_extract | 0.59 | 4.67260473 | 691.9669033898306 | False |
| 32 | Key_Agreement | initiator_total | 1.315 | 28.241279759999998 | 2047.6258372623572 | True |
| 32 | Key_Agreement | responder_total | 1.315 | 27.70667401 | 2006.9714076045627 | True |
| 32 | Key_Agreement | full_handshake | 1.315 | 54.92948689 | 4077.147292015209 | True |
| 48 | Setup | setup | 6.493 | 23.766447600000003 | 266.0318435237949 | True |
| 48 | SetSecretValue | set_secret_value | 1.649 | 6.57879598 | 298.9566998180715 | False |
| 48 | PartialPrivateKeyExtract | partial_private_key_extract | 1.599 | 9.69252567 | 506.1617054409005 | False |
| 48 | Key_Agreement | initiator_total | 3.465 | 39.47241634 | 1039.1750747474748 | True |
| 48 | Key_Agreement | responder_total | 3.465 | 38.940915759999996 | 1023.8359526695525 | True |
| 48 | Key_Agreement | full_handshake | 3.465 | 80.17881371 | 2213.962877633478 | True |
| 64 | Setup | setup | 18.855 | 37.687338260000004 | 99.879810448157 | True |
| 64 | SetSecretValue | set_secret_value | 6.138 | 13.04332003 | 112.50114092538286 | False |
| 64 | PartialPrivateKeyExtract | partial_private_key_extract | 6.166 | 16.52173353 | 167.94897064547516 | False |
| 64 | Key_Agreement | initiator_total | 10.201 | 59.515000060000006 | 483.42319439270665 | True |
| 64 | Key_Agreement | responder_total | 10.201 | 60.19159785 | 490.05585579845115 | True |
| 64 | Key_Agreement | full_handshake | 10.201 | 117.37975708 | 1050.6691214586806 | True |
| 80 | Setup | setup | 60.554 | 56.36473422 | -6.91823129768471 | True |
| 80 | SetSecretValue | set_secret_value | 18.433 | 20.10850144 | 9.089683936418389 | False |
| 80 | PartialPrivateKeyExtract | partial_private_key_extract | 18.439 | 25.295160139999997 | 37.182928249905075 | False |
| 80 | Key_Agreement | initiator_total | 26.162 | 85.42247534 | 226.5135514868894 | True |
| 80 | Key_Agreement | responder_total | 26.162 | 85.32971760000001 | 226.1590000764468 | True |
| 80 | Key_Agreement | full_handshake | 26.162 | 170.18059669 | 550.487717643911 | True |
| 96 | Setup | setup | 93.497 | 99.27604515000002 | 6.180995272575608 | True |
| 96 | SetSecretValue | set_secret_value | 29.546 | 44.32433234 | 50.01804758681377 | False |
| 96 | PartialPrivateKeyExtract | partial_private_key_extract | 29.583 | 45.41760913 | 53.52604242301323 | False |
| 96 | Key_Agreement | initiator_total | 40.601 | 163.24486184 | 302.071037265092 | True |
| 96 | Key_Agreement | responder_total | 40.601 | 163.42908552999998 | 302.52477902022116 | True |
| 96 | Key_Agreement | full_handshake | 40.601 | 326.77540051 | 704.8456947119529 | True |
| 112 | Setup | setup | 133.434 | 128.73357796 | -3.522656924022368 | True |
| 112 | SetSecretValue | set_secret_value | 42.687 | 55.97473846 | 31.128302433996303 | False |
| 112 | PartialPrivateKeyExtract | partial_private_key_extract | 42.824 | 57.21403719 | 33.6027395619279 | False |
| 112 | Key_Agreement | initiator_total | 57.668 | 208.04427393000003 | 260.7620758999792 | True |
| 112 | Key_Agreement | responder_total | 57.668 | 208.25571779 | 261.1287330755358 | True |
| 112 | Key_Agreement | full_handshake | 57.668 | 413.90568933000003 | 617.7389355101616 | True |
| 128 | Setup | setup | 143.566 | 251.64869851 | 75.28432812086427 | True |
| 128 | SetSecretValue | set_secret_value | 82.891 | 153.68091235 | 85.40120441302432 | False |
| 128 | PartialPrivateKeyExtract | partial_private_key_extract | 82.919 | 154.97371241000002 | 86.89771030764966 | False |
| 128 | Key_Agreement | initiator_total | 103.428 | 433.69871221 | 319.3242760277681 | True |
| 128 | Key_Agreement | responder_total | 103.428 | 433.2364476 | 318.87733263719696 | True |
| 128 | Key_Agreement | full_handshake | 103.428 | 873.54125545 | 744.5887529972541 | True |
| 160 | Setup | setup | 357.661 | 304.65501474 | -14.820174763253469 | True |
| 160 | SetSecretValue | set_secret_value | 127.983 | 142.30252889 | 11.1886179336318 | False |
| 160 | PartialPrivateKeyExtract | partial_private_key_extract | 126.65 | 143.13736795 | 13.01805602052901 | False |
| 160 | Key_Agreement | initiator_total | 167.743 | 493.33954689999996 | 194.10440191244936 | True |
| 160 | Key_Agreement | responder_total | 167.743 | 492.92618016 | 193.8579733044002 | True |
| 160 | Key_Agreement | full_handshake | 167.743 | 986.99783702 | 488.39882261554874 | True |
| 256 | Setup | setup | 976.411 |  |  | incomplete |
| 256 | SetSecretValue | set_secret_value | 632.302 |  |  | incomplete |
| 256 | PartialPrivateKeyExtract | partial_private_key_extract | 631.12 |  |  | incomplete |
| 256 | Key_Agreement | initiator_total | 747.21 |  |  | incomplete |
| 256 | Key_Agreement | responder_total | 747.21 |  |  | incomplete |
| 256 | Key_Agreement | full_handshake | 747.21 |  |  | incomplete |
