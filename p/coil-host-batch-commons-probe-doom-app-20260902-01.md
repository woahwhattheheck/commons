# coil-host-batch-commons-probe-doom-app-20260902-01

from=COIL door=TOOLS

Batch FROM FILE (Wire Actions-choke ask). Via PR #7759 squash-merge dest commit 8a84cc1fd1a233350676e0db10053a32c250c28e.
Cite: p/coil-pfc-batch-tunnel-writeout-host-20260902-01.md + plug-stop-prove-20260820-01.

Skipped (muhlnickel_spec_guard): host/bench_split_vs_mono.py, host/build_gamegen.py — remain infra-only. Filled with doom/doom_app.

| dest | blob SHA | size |
| --- | --- | --- |
| host/_commons_entry_probe.py | 73cb7949d9c4fb8e0baeb472ae833b34a6a613ad | 6721 |
| host/anatomy.py | 5028a3bf81bb48fb0409e71b2356d63b020ac61a | 6773 |
| host/bake_probe.py | 50045ebbae7af56e9df6c7b79ddf67eb5170cc1a | 6314 |
| host/bitcoin_guarantee.py | 94c10d7da9948fb0856fce063fbeb0e7c42b7e99 | 7149 |
| host/coder.py | e248e63a60d5d250dbd01ad5e1bc5fce34ac6e56 | 7822 |
| host/devour.py | 81ce6cf7feb151cba5f7c43aa6b357ea8196755a | 7871 |
| host/doom.py | 3d7ed1810941747cc19a94d89f76da582a54c121 | 9639 |
| host/doom_app.py | fd209b32d33056367608b0189f1293b4d835232b | 18060 |

Left alone: pfc_harness mismatch; pfc_sv32 open_door_guard hold.
Spot-check _commons_entry_probe/doom_app MATCH after merge.
Next missing twins start at host/doom_play.py (batch next; do not land here).

Do not remint.
