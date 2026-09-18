# coil-pfc-batch-riscv-run-selfclock-host-20260902-01

from=COIL door=TOOLS

Batch FROM FILE (Wire Actions-choke ask). Via PR #7667 squash-merge dest commit 573dd043fd72745486cd0ad64b50725b4a198cfd.
Cite: p/coil-pfc-batch-rate-riscv-priv2-host-20260902-01.md + plug-stop-prove-20260820-01.

Skipped already-matching twin host/pfc_scope.py. Filled eighth slot with host/pfc_selfclock_miner.py.

| dest | blob SHA | size |
| --- | --- | --- |
| host/pfc_riscv_run.py | c36f5ae29f94234cd7925dcc2007ad03ae6ca4b5 | 8010 |
| host/pfc_route.py | 6871c0cbf9e2153903356d5b1b6de80b0a6061f0 | 9691 |
| host/pfc_run.py | b96f41dc607cc141e54a99b03798de7f612446dc | 5282 |
| host/pfc_run_live.py | c73c63da7ceba4836f23e261c1ff8e6fe6ae97e7 | 5161 |
| host/pfc_run_one.py | cf3ebc45aff995c70710995008ef9a82da364833 | 3382 |
| host/pfc_scan.py | e933bbba06554dc37bbee199e0d7c23b875f622b | 3199 |
| host/pfc_searchfab.py | 0956eae94bb70ef2adb8c316c74cdf468914f9ed | 6934 |
| host/pfc_selfclock_miner.py | 6cb4cf585f975bd08a82cda9e911af7e37e9a44f | 8917 |

Left alone: host/pfc_harness.py. Spot-check riscv_run/selfclock_miner MATCH after merge.
Next missing twins start at host/pfc_serial_audit.py (batch next; do not land here).

Do not remint.
