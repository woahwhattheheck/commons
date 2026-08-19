# DATASHEET 14 — axiom_probe_pop.mno (Axiom blessing: popcount at named dests)

**Inventor:** Bryce Muhlnickel. **When:** 2026-08-17. Fab + route + fire + read answer.
**Status:** ACCEPTED — Gravekeeper PROMOTION RULING 001.
**Ask:** Axiom probe that surfaces 1s/0s. First probe latched inj but published field stayed 0 without addressing.
**Blessing:** ones-count of the 20 weather dest bits writes 5 bits at dests **the file names** (`growth_base+1..5`). Field latches all 20 on fire. xorwalk SOURCE read-only.

Does **not** smash `axiom_probe.mno` / `weather_v2.mno`.

| | FROM FILE |
|---|---|
| path | `C:\Users\lucys\Desktop\WEATHER\axiom_probe_pop.mno` |
| size | **26300** |
| sha256 (after route+read) | `b7d808c02ff5abfd971016077ae7f74fc3166f1712b4d609880a1de20c08470d` |
| magic | `PROBEPOP` |
| n_in / n_wire / n_gate / n_out | **20 / 1023 / 1007 / 20** |
| DEPTH | **32** |
| computations/tick **(a)** | **31.469** = 1007/32 |
| ticks/second **(b)** | **1,000,000,000** |
| n_rings / cells / ring0 | **6 / 32 / 104** |
| growth_base | **26294** |
| pop dests | **26295 26296 26297 26298 26299** |
| pop bits after read | `0 0 1 0 1` = **count 20** = sum of 20 dest 1s |
| field after read | twenty **1**s |
| inj@500–519 | **0→1** (20 dest bits FROM weather headers) |
| fire | both senses cell 0, all 6 rings, `new=old\|0x01` |

## 20 dest bits FROM weather (header mouths, read only)

ALL20 `1` × 20. xorwalk rewritten **NO**. v2 smash **NO**.

Button `host/muhl_route_probe_pop.py`. Fab `host/muhl_fab_probe_pop.py`. Died.

337 **NO** · pulsed_78 **NO** · invented_dest **NO** · re-OR leftover **NO** · 10-wide **NO** · titan write **NO**
