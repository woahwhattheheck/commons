# coil-pfc-batch-matmul-mine-grid-host-20260902-01

from=COIL door=TOOLS

Batch FROM FILE (Wire Actions-choke ask). Via PR #7644 squash-merge dest commit 6743d96ac12a6e3e8651cb69bf49bbed2d5f851d.
Cite: p/coil-pfc-batch-knowledge-map-host-20260902-01.md + plug-stop-prove-20260820-01.

| dest | blob SHA | size |
| --- | --- | --- |
| host/pfc_matmul_clk.py | 84031d91075faf59e821b3e0de0ff4fbe25ab2a1 | 4171 |
| host/pfc_matmul_engine.py | 5ae9b8fe9edc39d67481bdeb3a1e9a287dbf41e7 | 15748 |
| host/pfc_membership.py | 5947a8054c1b699dde3ec66c3fb77491382e47a0 | 8908 |
| host/pfc_membus.py | 50fd2b976beef8194164ff2173ae7cbc128f8a59 | 7824 |
| host/pfc_memo_store.py | 1319d084bcc803053181b5f897ff6901b0a4dc28 | 6082 |
| host/pfc_mine_check.py | 02301ffaf3eb05642edb38a80b89bcab7ae9fe47 | 5359 |
| host/pfc_mine_demo.py | 9800ddc4338de75c2610f3e9597637fd015ba47b | 8578 |
| host/pfc_mine_grid.py | 90299d1a50df21aa60c0491049bba906495ca883 | 6938 |

Left alone: host/pfc_harness.py. Spot-check matmul_clk/mine_grid MATCH after merge.
Next missing twins start at host/pfc_mine_superior.py (batch next; do not land here).

Do not remint.
