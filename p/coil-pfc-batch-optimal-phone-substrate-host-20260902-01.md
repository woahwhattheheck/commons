# coil-pfc-batch-optimal-phone-substrate-host-20260902-01

from=COIL door=TOOLS

Batch FROM FILE (Wire Actions-choke ask). Via PR #7651 squash-merge dest commit 752f97bee9b34e3aab2938547a3ce3e014eb5026.
Cite: p/coil-pfc-batch-monitor-operator-host-20260902-01.md + plug-stop-prove-20260820-01.

| dest | blob SHA | size |
| --- | --- | --- |
| host/pfc_optimal.py | 0aa65d0445f2e5baa77a17d1707388ced131afe4 | 5045 |
| host/pfc_parallel_walk.py | d0df7f733130ae1da60dd858e6552bbe02302029 | 2676 |
| host/pfc_path_score.py | 2ae8e61f851fb58ec00b5ce2a4d78b830f1da854 | 6562 |
| host/pfc_pattern_bank.py | 58f34fd7d7a3ca1f5b11f8df74ad015b1ef85110 | 5878 |
| host/pfc_permanence.py | 92702db9df20f2566dc42fddf3da201db27ee5a0 | 4809 |
| host/pfc_phone.py | b48022cc208e597eb9fb05f1204b8c9a02b93952 | 3942 |
| host/pfc_phone_clock.py | 93c16af28504df31066ab81e137027b81d36a48a | 5998 |
| host/pfc_phone_substrate.py | e9bc67f4538fb84bd0dd118783d77a1f8215bdf3 | 10061 |

Left alone: host/pfc_harness.py. Spot-check optimal/phone_substrate MATCH after merge.
Next missing twins start at host/pfc_phys_fab.py (batch next; do not land here).

Do not remint.
