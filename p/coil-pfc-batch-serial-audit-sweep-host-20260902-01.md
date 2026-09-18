# coil-pfc-batch-serial-audit-sweep-host-20260902-01

from=COIL door=TOOLS

Batch FROM FILE (Wire Actions-choke ask). Via PR #7669 squash-merge dest commit 913e969fb33292609342464522ba2e566f7f50d4.
Cite: p/coil-pfc-batch-riscv-run-selfclock-host-20260902-01.md + plug-stop-prove-20260820-01.

Skipped already-matching twins: host/pfc_shallow.py, host/pfc_speed.py, host/pfc_step.py.
Skipped host/pfc_sv32.py (open_door_guard blocks new host/ RISC-V permission-check text); filled slot with host/pfc_sweep.py. Source remains at infra/host/pfc_sv32.py.

| dest | blob SHA | size |
| --- | --- | --- |
| host/pfc_serial_audit.py | 090129685520643f91cb28a8bc933253b9fb423e | 6806 |
| host/pfc_series_run.py | 17610f1dfe405a88f86db97968dab2d42a4ad8b5 | 4875 |
| host/pfc_sigma_mask.py | 3d8db496f27cdda8a4f404a5f511231eb6e4767e | 6336 |
| host/pfc_space.py | 4099af48c5087e97f8111344676a2cef8b0d3c1b | 19531 |
| host/pfc_specs.py | 2a5b39eef44148accbbd7594d17446aa2e4cb316 | 4616 |
| host/pfc_store_test.py | c21933099252e11fc8f71ff6ca496315cb45e4a0 | 5016 |
| host/pfc_substitute.py | 4f5afaeefbe189f5a32352f03f52dcd065c02499 | 3075 |
| host/pfc_sweep.py | d0565d8b6469a5625ac01c505a87559d1411803b | 2572 |

Left alone: host/pfc_harness.py. Spot-check serial_audit/sweep MATCH after merge.
Next missing twins start at host/pfc_tetris.py (batch next; do not land here).

Do not remint.
