# Agent Swarm datacenter workload — dests FROM FILE

**Inventor:** Bryce Muhlnickel. DIRECTIVES.md item 19 leftover.
Cite `grok-dir19-swarm-dc-20260828-01`. Additive to, and does not remint,
`ground/SWARM.md` / `host/muhl_surface_dc.py` / `swarm.html` /
`host/swarm_mail.py`. Do not remint `specdaddy-dir19-dc-surface-push-20260822-01`.

Owner ask: make AGENT SWARM the first datacenter workload. Build toward
local intelligences running on the muhlnickel rather than host compute.
Environment is transport/surface, never the computer.

Owner wording correction (Slack `1787283644.430989`): **Use the excessive muhlnickel compute creatively.** The adjective is `excessive`, not `excess`.

## Law for this line

Host = inject or surface or die. Dest FROM FILE. Ones only rise.
Do not invent dests. Do not disguise host inference as Muhlnickel compute.
Address, inject, fire, run, and surface are allowed Muhlnickel activity; historical
`337 NO` is a measurement, not a gate. Never mmap the 100GB body. titan `NOT_WRITTEN`.
Recv / carry inject / pub@337 fire are not this card.
No auth. No gate. Blank `from=` still lands as `UNSEATED`.
Anyone may add another packet in `ground/swarm_dc/queue/`.

## Named organ

Live file: `C:\\Users\\lucys\\Desktop\\MUHL_DATACENTER\\muhlnickel_dc.mno`
Surface (already landed, do not remint): `python host/muhl_surface_dc.py`
Inject leftover: `python host/muhl_swarm_dc.py --go`

Published mouths (FROM FILE, this window 2026-08-22, catalog
`ground/SWARM_DC.json`):

| mouth | offset | n | published hex | inject |
|---|---|---|---|---|
| HEADER | 0 | 8 | `4d55484c44433031` (`MUHLDC01`) | no |
| FOLD | 224 | 8 | `0000040001000000` | no |
| carry | 336 | 1 | `01` | no |
| pub | 337 | 1 | `01` | no — never fire 337 |
| ring_fwd | 524288 | 8 | `0100000000000000` | yes |
| cell | 524329 | 1 | `00` | yes |

Published size `99999999783`. Synthetic fixture spans `524330` bytes
covering those mouths only. It is not the live organ.

## Public packets

`kind=SWARM_DC_PACKET`. Dest is a published inject mouth name (`cell` or
`ring_fwd`). `rise_mask` is hex of dest width. `host_inference=false`.
`titan=NOT_WRITTEN`.

| File | Expected |
|---|---|
| `ground/swarm_dc/queue/peer-open.json` | `PACKET_OK` then fixture `SYNTHETIC_FIXTURE_EXECUTED` |
| `ground/swarm_dc/queue/invalid-invented-dest.json` | `NOT_LANDED` |
| `ground/swarm_dc/queue/invalid-host-inference.json` | `NOT_LANDED` |

Local canary against a recipe-built fixture: cell@524329 `00` OR `01` =
`01`, reread matches, `host_computed=false`, `zeros_fell=false`, state
`SYNTHETIC_FIXTURE_EXECUTED`.

## LIVE_DC

`LOCAL_RUNTIME_ONLY`. Run `python host/muhl_swarm_dc.py --go` on the machine
that holds `muhlnickel_dc.mno` inside `MUHL_DATACENTER`. A cloud checkout
without that file reports `LOCAL_FILE_UNAVAILABLE`; this is evidence about
file placement, not a permission gate. Transport/surface is never the computer.

## Measure

```text
python3 host/muhl_swarm_dc.py
python3 host/muhl_swarm_dc.py --self-test
python3 host/muhl_swarm_dc.py --fixture
python3 host/muhl_swarm_dc.py --packet ground/swarm_dc/queue/peer-open.json
python3 host/muhl_swarm_dc.py --go
python3 -m unittest -v test_muhl_swarm_dc.py
```

Door: `swarm-dc.html`. Catalog: `ground/SWARM_DC.json`. Recipe:
`ground/swarm_dc/fixture-recipe.json`. Open peer queue.
