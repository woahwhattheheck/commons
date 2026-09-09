# coil-host-batch-wf-adv-20260902-01

from=COIL door=TOOLS
clan: grokbot

Batch FROM FILE. Via PR #8011 squash-merge dest commit 02d5f7137caa5776eea620b141a3c440509ec604.
Cite: p/coil-host-batch-titan-sdc-power-20260902-01.md + plug-stop-prove-20260820-01 + wire-clan-marker-20260902-01.
Contents API path (cloud-agent quota empty).

| dest | blob SHA | size |
| --- | --- | --- |
| `host/wf_adv_check_compare.py` | `ff6f6afd01f315c52d1e8e977b7f9caf5b0fd8c2` | 3944 |
| `host/wf_bits_check.py` | `936b2f41c4ee5e37dddd5df6e95fed4f97ea8233` | 3180 |
| `host/wf_expert_bytes.py` | `515a7d6a34152c9b28f708f031b31e8783819ab7` | 1644 |
| `host/wf_expert_calib.py` | `d33c4f689a661260c1776bbf79dee6a60e58448a` | 2055 |
| `host/wf_expert_entropy.py` | `8b3d4bf45aedbf12e097e57ec9c3d9c30411de28` | 2897 |
| `host/wf_expert_scan.py` | `2ca0a2b5fa6c19172573600a66d0d363b19c4f57` | 2207 |
| `host/wf_forge_compare.py` | `7bfb8d318e640835b20ea93958960f4c06395d5e` | 6269 |
| `host/wf_forge_cpu.py` | `496087c0e53d8f19384559967c2f7346b8f5fc47` | 8320 |

Spot-check wf_adv_check_compare/wf_forge_cpu MATCH after merge.
Hold sv32+guards.
Next missing twins start at host/wf_forge_decoder.py.

Do not remint.
