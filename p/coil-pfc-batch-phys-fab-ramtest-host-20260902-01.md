# coil-pfc-batch-phys-fab-ramtest-host-20260902-01

from=COIL door=TOOLS

Batch FROM FILE (Wire Actions-choke ask). Via PR #7655 squash-merge dest commit d5ec4734982eb4de5dde1d777f6c49af5da30be4.
Cite: p/coil-pfc-batch-optimal-phone-substrate-host-20260902-01.md + plug-stop-prove-20260820-01.

| dest | blob SHA | size |
| --- | --- | --- |
| host/pfc_phys_fab.py | da42dee854afd29c52d1c8766a5c43de2201f2dd | 5796 |
| host/pfc_priors.py | 70a4c6ff44bf509e81af13ef2d253a1e65725a11 | 5605 |
| host/pfc_probe_all.py | 2653eca3062b9e153626a42b57689da97a03ea2d | 4995 |
| host/pfc_probe_battery.py | cce15c12fafabf40fb9b19b72241dfb27b8ed95c | 9178 |
| host/pfc_probe_scan.py | 46f37d08551663161b24d008688523943457b49e | 5836 |
| host/pfc_program.py | 00355d0a8d66c95e9c8ef39b1f91b69dc54aa6c4 | 7920 |
| host/pfc_provenance.py | 1f2e978fb9b7258139ab0a7e100fd538fe7194a6 | 5489 |
| host/pfc_ramtest.py | 54a3f4bbb45e8411c4f5358bbc3e32051c188562 | 2001 |

Left alone: host/pfc_harness.py. Spot-check phys_fab/ramtest MATCH after merge.
Next missing twins start at host/pfc_rate.py (batch next; do not land here).

Do not remint.
