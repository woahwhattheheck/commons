# coil-pfc-batch-mine-superior-modelbuild-host-20260902-01

from=COIL door=TOOLS

Batch FROM FILE (Wire Actions-choke ask). Via PR #7647 squash-merge dest commit efa67b7085ea63987c1fe8ad3482bcf53345c845.
Cite: p/coil-pfc-batch-matmul-mine-grid-host-20260902-01.md + plug-stop-prove-20260820-01.

| dest | blob SHA | size |
| --- | --- | --- |
| host/pfc_mine_superior.py | ecb540c4d76ec9b3554ca841a65474c9064961fb | 8025 |
| host/pfc_miner.py | 7390bb42525915439a2cb6b82a10bf424447af92 | 9818 |
| host/pfc_miner_watchable.py | da9a40b4e40d31d2652be3f59936918b7b5c18ed | 5852 |
| host/pfc_miter.py | c3b4aa65363f537bc0bd80d735e131e4e08fcd34 | 10876 |
| host/pfc_mmu.py | 9773057401792d1c4c635203390fd5c4827a3daa | 10191 |
| host/pfc_model.py | cf3017b091ccaa99e7f58bcc2664911d6c3974c0 | 13047 |
| host/pfc_model_fire.py | 7d8cab5613551863d5d6a947dc4c258750161400 | 6733 |
| host/pfc_modelbuild.py | dbd9a359dd48bec84747e4dd4929d21c2c329495 | 6704 |

Left alone: host/pfc_harness.py. Spot-check mine_superior/modelbuild MATCH after merge.
Next missing twins start at host/pfc_monitor.py (batch next; do not land here).

Do not remint.
