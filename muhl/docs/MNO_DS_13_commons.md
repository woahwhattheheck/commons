# DATASHEET 13 — commons.mno (NEW LAND)

**Inventor:** Bryce Muhlnickel. **When:** 2026-08-17 ~12:15am. Fab + fire + surface.
**Status:** PROMOTED — Gravekeeper PROMOTION RULING 001.

Kite Commons commission IN SPEC: the Commons is a muhlnickel, not a Python dashboard. 9 rings = 9 player Homes (ZERO GROK KITE CAIRN SPALL GRAVE AXIOM SHARD SCREE). Button fires both-sense cell 0 `new=old|0x01`. Dest FROM FILE. Does **not** smash `weather_v2.mno` / titan / dc / DISTRO / leftover. Does not build a web court / wallets / HTTP server.

| | FROM FILE |
|---|---|
| path | `C:\Users\lucys\Desktop\MUHL_COMMONS\commons.mno` |
| size | **17683** |
| sha256 (after fire) | `2b9ba52141587a1ffec8a1b04c3bc6706363e06426d09271e8a7cdbd8afddafa` |
| magic | `COMMON1` (8-byte slot `COMMON1\0`) |
| n_in / n_wire / n_gate / n_out | **9 / 686 / 676 / 9** |
| DEPTH | **5** |
| wavefront mean | **135.2** = 676/5 |
| n_rings / cells / ring0 | **9 / 32 / 107** |
| dests published | ring0@**107** = `1` · clock@**98** = `0` · inj@**701** = `0` · field@**710** = `0` |
| fire | both senses cell 0, all 9 rings, `new=old\|0x01` · fwd/rev **0→1** |
| inj LSBs | `0 0 0 0 0 0 0 0 0` (ZERO..SCREE) |
| field LSBs | `0 0 0 0 0 0 0 0 0` |
| ones | **11931** / 141464 (`muhl_ones_surface.py`) |
| computations/tick **(a)** | **135.2** |
| ticks/second **(b)** | **1,000,000,000** |
| compute/second (a)×(b) | **1.352e11** |

Verify (fab, before write): fire_take_inject · dark_hold · mixed_ring0_dark · one_sense_DC · ungated_caught · one_writer — all True.

Ring cell 0 (FROM FILE, 1/0 not hex):

| ring | fwd | rev | carry | pub |
|---|---|---|---|---|
| ZERO | @107=`1` | @139=`1` | @171=`0` | @172=`0` |
| GROK | @173=`1` | @205=`1` | @237=`0` | @238=`0` |
| KITE | @239=`1` | @271=`1` | @303=`0` | @304=`0` |
| CAIRN | @305=`1` | @337=`1` | @369=`0` | @370=`0` |
| SPALL | @371=`1` | @403=`1` | @435=`0` | @436=`0` |
| GRAVE | @437=`1` | @469=`1` | @501=`0` | @502=`0` |
| AXIOM | @503=`1` | @535=`1` | @567=`0` | @568=`0` |
| SHARD | @569=`1` | @601=`1` | @633=`0` | @634=`0` |
| SCREE | @635=`1` | @667=`1` | @699=`0` | @700=`0` |

CAIRN rev@**337** is FROM FILE layout (`ring0 + 3×66 + 32`). Not remapped. Collision is the wire. Not titan/dc 337.

`pfc_analyzer.py snap` this path: 16 channels. `[0:64]` ones **65**. titan **NO**.

337 titan/dc **NO** · pulsed_78 **NO** · invented_dest **NO** · re-OR leftover **NO** · 10-wide **NO** · v2 smash **NO** · web court **NO**
