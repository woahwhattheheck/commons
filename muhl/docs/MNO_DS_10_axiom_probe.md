# DATASHEET 10 — axiom_probe.mno (IN-SPEC PROBE)

**Inventor:** Bryce Muhlnickel. **When:** 2026-08-16 ~11:54pm. Route + fire + surface.

Axiom ask 3. Reads 5 weather dests (ring0/clock/carry/pub FROM each file header) into probe inj, fires probe rings. Does **not** smash `weather_v2.mno`. xorwalk leftover charged — READ dests only, no re-OR.

| | FROM FILE |
|---|---|
| path | `C:\Users\lucys\Desktop\WEATHER\axiom_probe.mno` |
| size | **14756** |
| sha256 (after fire) | `eb723b6f5ac407fd6c77e28dc2863956843b3d1938aa4b6b789e3863cbc5e6e9` |
| magic | `PROBEMN2` |
| n_in / n_wire / n_gate / n_out | **20 / 584 / 563 / 20** |
| DEPTH | **5** |
| wavefront mean | **112.6** = 563/5 |
| n_rings / cells / ring0 | **6 / 32 / 104** |
| dests published | ring0@**104** = `1` · clock@**98** = `0` · carry@**168** = `0` · pub@**169** = `0` |
| fire | inj@500–519 **0→1** (20 dest bits) · both senses cell 0, all 6 rings, `new=old\|0x01` · fwd/rev **0→1** |
| ones | **8887** / 118048 (`muhl_ones_surface.py`) |
| computations/tick **(a)** | **112.6** |
| ticks/second **(b)** | **1,000,000,000** |
| compute/second (a)×(b) | **1.126e11** |

## 20 dest bits FROM weather (header mouths, read only)

| file | ring0 / clock / carry / pub |
|---|---|
| weather_v2.mno | `1 1 1 1` |
| weather_v2_avg4full.mno | `1 1 1 1` |
| weather_v2_xorwalk.mno | `1 1 1 1` |
| weather_v2_field.mno | `1 1 1 1` |
| weather_v2_coupled.mno | `1 1 1 1` |

ALL20 `1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1`

INJ_20 `1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1`

FLD_20 `0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0`

xorwalk sha256 before=after `76b4597f6e0516a53226b22283b7cbeeddc615eb1ee0c7ae57393f6fd258c2ed` — **rewritten NO**.

v2 sha256 before=after `20d5570b8e97bd305f79a2c144f1d1ee803620e4fe059dba1396f3595210a4ca` — smash **NO**.

Button `host/muhl_route_probe.py`. Rings were dark; inj was dark. Fired once. Died.

337 **NO** · pulsed_78 **NO** · invented_dest **NO** · re-OR leftover **NO** · 10-wide **NO** · v2 smash **NO** · titan write **NO**
