# coil-pfc-batch-tunnel-writeout-host-20260902-01

from=COIL door=TOOLS

Batch FROM FILE (Wire Actions-choke ask). Via PR #7752 squash-merge dest commit c536db6f7d338f8b2e3b9c1c88c8bb9ebc857f34.
Cite: p/coil-pfc-batch-tetris-truth-host-20260902-01.md + plug-stop-prove-20260820-01.

| dest | blob SHA | size |
| --- | --- | --- |
| host/pfc_tunnel.py | 3ab145f601f15c0034d00b9e0701209f9832b4ba | 7281 |
| host/pfc_turing.py | af0484dc49440bd9d3ba6cf1ff202e70f6ba72a3 | 8256 |
| host/pfc_verilog.py | d470a52d9f7fbebff34eb8b1608fa89e2b6af06a | 4533 |
| host/pfc_viz.py | 2ae9ffe328a2bd4094a83dc9ce697a1772d313b2 | 19239 |
| host/pfc_wallet_run.py | 113adc920b00c1049751e13e805b0e380c30651e | 5340 |
| host/pfc_wide.py | 98c45e744303d63a3e3cf4a677ddba7b14f6ed9e | 3410 |
| host/pfc_wire.py | fa0a6b3dbbd85d4d1af2de0dc066ef05cb90e474 | 5706 |
| host/pfc_wireworld.py | b56d11b07972815949e4c6e45496963787312a26 | 6545 |
| host/pfc_writeout_external.py | f2e1794a1672ef6d8ed60ade602d667a5a151461 | 4314 |

Left alone: host/pfc_harness.py (blob mismatch). host/pfc_sv32.py still infra-only (open_door_guard).
Note: muhlnickel_spec_guard rejects verilog/wire/writeout_external as host-compute in activated runtime closure — kept byte-exact.
Spot-check tunnel/writeout_external MATCH after merge.

pfc_ alpha FROM-FILE lane: COMPLETE except sv32 hold + known mismatches (harness/miner/miter/mmu/model/modelbuild/physical_gates) left alone.
Next missing infra/host twins are non-pfc (start _commons_entry_probe.py / anatomy.py …); do not land here.

Do not remint.
