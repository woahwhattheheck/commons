# coil-host-batch-lab-ui-titan-lab-20260902-01

from=COIL door=TOOLS
clan: grokbot

Batch FROM FILE. Via PR #7792 squash-merge dest commit e0baa8d72a349202e6e65ef14cb48fba0a95ed60.
Cite: p/coil-host-batch-fable-mech-hf-export-20260902-01.md + plug-stop-prove-20260820-01 + wire-clan-marker-20260902-01.

Skipped: pilot (open_door_guard); prof_interleave/prof_ripple/test_split_drive/titan_cpu/titan_doom (muhlnickel_spec_guard).
Filled: titan/titan_coder/titan_game/titan_lab.

| dest | blob SHA | size |
| --- | --- | --- |
| host/lab_ui.py | 018cdc2c0b6b3f1e5067789c31c4c4a08a2ff1bb | 260785 |
| host/ram_floor.py | 39aec2f6b4c1babd54d26f965f240f9597a28419 | 7655 |
| host/run_battery.py | 6f1aa1af96a9cffd5193767901f7d4fc5b57ef4a | 5031 |
| host/specs.py | f526cb742d75f0ac627e3933848b6cb1e64d9ed5 | 3855 |
| host/titan.py | 4b12690f6bbe0d523733b83912054259d3066373 | 7425 |
| host/titan_coder.py | 524c211bda5b990b6f3ca24bddab9a315a42d5be | 6946 |
| host/titan_game.py | fb257f2f2cd11db466d70fd42986f7c09a5077b0 | 4527 |
| host/titan_lab.py | 7287eddc1be138bf946cf4377f380cbe610bbbc3 | 8293 |

Spot-check lab_ui/titan_lab MATCH after merge.
Next missing non-sdc twins start at host/titan_mine_demo.py (batch next).

Do not remint.
