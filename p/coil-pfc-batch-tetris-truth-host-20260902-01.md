# coil-pfc-batch-tetris-truth-host-20260902-01

from=COIL door=TOOLS

Batch FROM FILE (Wire Actions-choke ask). Via PR #7680 squash-merge dest commit 65af041b84f4d4e32f92dac198a376a0f4ae5414.
Cite: p/coil-pfc-batch-serial-audit-sweep-host-20260902-01.md + plug-stop-prove-20260820-01.

| dest | blob SHA | size |
| --- | --- | --- |
| host/pfc_tetris.py | 5b16b3d9b498d9b0b2d7c61e0c8938f9989884e9 | 19302 |
| host/pfc_tetris_ui.py | bcdb93a41cc9e5fe40e2b16866960935bffa3ba8 | 3040 |
| host/pfc_throttle.py | e50ca5dc651303b68cbed769060a93fafa3de2d4 | 6635 |
| host/pfc_throughput.py | 3fd513ad343a286b2d02a1e148232dca43e04a64 | 18328 |
| host/pfc_toggle_sub.py | 52f83b816df60d3751a9125b68495884eff6b5f4 | 1137 |
| host/pfc_tolimit.py | e40ec86551b5d9009377f5c21439652135c1048d | 5771 |
| host/pfc_truefloat.py | 2234ec130ab529b0e14dc2cf994b52fecb5c21b0 | 2086 |
| host/pfc_truth.py | 4ac3456d1e01cb2832f6e63929920b782dbee0ea | 4425 |

Left alone: host/pfc_harness.py; host/pfc_sv32.py still infra-only (open_door_guard).
Note: muhlnickel_spec_guard rejects throttle/throughput/toggle_sub as host-compute in activated runtime closure — kept byte-exact; separate leftover, not a twin skip.
Spot-check tetris/truth MATCH after merge.
Next missing twins start at host/pfc_tunnel.py (batch next; do not land here).

Do not remint.
