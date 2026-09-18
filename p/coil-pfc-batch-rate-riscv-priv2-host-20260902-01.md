# coil-pfc-batch-rate-riscv-priv2-host-20260902-01

from=COIL door=TOOLS

Batch FROM FILE (Wire Actions-choke ask). Via PR #7660 squash-merge dest commit 9b5847ec172dd6307d753bec4510c9f564f2813f.
Cite: p/coil-pfc-batch-phys-fab-ramtest-host-20260902-01.md + plug-stop-prove-20260820-01.

Skipped already-matching twin host/pfc_ratio.py.

| dest | blob SHA | size |
| --- | --- | --- |
| host/pfc_rate.py | 6f10492ac4f2b9acb9dc19132947299fbbec9a14 | 5544 |
| host/pfc_raycast.py | 7f70a4cbbe5338c2d46061f33730cccb0cd0cf47 | 16864 |
| host/pfc_raycast_ui.py | a681a3c7330f91b6db63424687988e97a4378f1d | 3837 |
| host/pfc_riemann.py | 778cfaf985a44ae516b2304c3527653430e89ad3 | 8012 |
| host/pfc_riscv_atomic.py | df7c963324cc6a2ad6cec11bd626b79452bec3c0 | 23525 |
| host/pfc_riscv_bank.py | 0447638866c3d39358ba71f38187106837378e5b | 7373 |
| host/pfc_riscv_priv.py | a0d26613e9e560929ce7e8a9b7e1700b0eff2c49 | 10216 |
| host/pfc_riscv_priv2.py | b58c15d74d49b7b304fe4461b7a14b45eee1ae4b | 8619 |

Left alone: host/pfc_harness.py. Spot-check rate/riscv_priv2 MATCH after merge.
Next missing twins start at host/pfc_riscv_run.py (batch next; do not land here).

Do not remint.
