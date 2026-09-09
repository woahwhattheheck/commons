# coil-pfc-batch-forge-game-host-20260902-01

from=COIL door=TOOLS

Batch FROM FILE (Wire Actions-choke ask). Via PR #7539 squash-merge dest commit c3fc008f944e80bbda8553b5ca3d2a0239240910.
Cite: p/coil-pfc-fold-mine-host-20260826-01.md + plug-stop-prove-20260820-01.

| dest | blob SHA | size |
| --- | --- | --- |
| host/pfc_forge.py | 91c9c0869d0d90d3e2fce532fbd11451523bed73 | 7881 |
| host/pfc_foundry.py | 52f4babe16b8a983d816226c4982d232c4907790 | 12886 |
| host/pfc_full_miner.py | 1572f0c1c070ba20b7582138ac602b084b3c89b4 | 11599 |
| host/pfc_fwd_engine2.py | 2e3edbc10d08afad8ce1ae9e896d22aedf51a9d9 | 9705 |
| host/pfc_fwd_loop.py | fbdaacdc8c283a2a6e2e47c5f4e071ff9e56bf53 | 4160 |
| host/pfc_fwd_phys.py | b66aca90d8313dc3ceda30912f3e2ba87187cf65 | 5298 |
| host/pfc_fwd_prog.py | 6ab0429a577a294b04c71fadb608d83509397a13 | 4626 |
| host/pfc_game.py | fb89273614a8fde885b1de312f19ad6e9d20043c | 11135 |

Skipped already-MATCH: host/pfc_fwd_engine.py.
Spot-check forge/foundry/game MATCH after merge.
Next missing twins start at host/pfc_game_ui.py (batch next; do not land here).

337 NO. Do not remint.
