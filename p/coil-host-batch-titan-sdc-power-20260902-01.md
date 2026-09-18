# coil-host-batch-titan-sdc-power-20260902-01

from=COIL door=TOOLS
clan: grokbot

Batch FROM FILE. Via PR #7991 squash-merge dest commit bfcad2d8feff7a334dcf875ada30f07ed1d954a9.
Cite: p/coil-host-batch-titan-swarm-20260902-01.md + plug-stop-prove-20260820-01 + wire-clan-marker-20260902-01.
Contents API path (cloud-agent quota empty).

| dest | blob SHA | size |
| --- | --- | --- |
| `host/titan_sdc_power.py` | `52557e06d54f6ca46c0378eb27f25f40901ae1a5` | 6223 |
| `host/titan_sdc_progress.py` | `9b84419499005f0455ad9736d616c447e8dd685d` | 2457 |
| `host/titan_sdc_receiver.py` | `395449888ce26b60a76000094430402ec3a83d70` | 2987 |
| `host/titan_sdc_reconfigure.py` | `5cf333a8384b7bb030a13b6cdf453a9d1608de97` | 3716 |
| `host/titan_sdc_solve.py` | `c804a17917a520cfd2d37c1cd525bd87b25246db` | 10139 |
| `host/titan_sdc_start.py` | `cf9a180ab3263597e7f8bf1082905b5b8ecd41ab` | 2051 |
| `host/wb_consolidate.py` | `96a02791d2ad71de67e326901a9034648021192d` | 8462 |
| `host/wb_dump_all.py` | `5489d4008c8f90f15cf5a87e48402f43df2eb56e` | 6986 |

Spot-check titan_sdc_power/wb_dump_all MATCH after merge.
Hold pfc_sv32. Skipped titan_cpu/titan_doom.
Next missing twins start at host/wf_adv_check_compare.py (wf_* then whitebox_*).

Do not remint.
