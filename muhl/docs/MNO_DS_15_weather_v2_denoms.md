# DATASHEET 15 — weather_v2_denoms.mno (TEAM STONE denominator cut #2)

**Inventor:** Bryce Muhlnickel. **When:** 2026-08-17. Fab + fire + surface + independent walk.
**Request:** `MUHL_GO/TEAM_STONE_BUILD_REQUEST.md` — Cairn p4, Spall p7.
**Status:** PROMOTED — Gravekeeper PROMOTION RULING 001. Fabricator did not certify itself.

32×32 numerator held. DEPTH 24→**22** by prefix **P = A|B** (XOR only on the sum bits). Byte-exact `(N+S+E+W)>>2`. Mutants caught. Does **not** smash `weather_v2_shallow_acre.mno` / `weather_v2_acre.mno` / `weather_v2.mno`.

Independent walker (not the fab): `WEATHER\muhl_walk_weather1_depth.py` — records_DEPTH **22** match YES.
Per-cell chain: `WEATHER\weather_v2_denoms_DEPTH.md`. Format: `WEATHER\WEATHER1_FORMAT.md`.

| | FROM FILE |
|---|---|
| path | `C:\Users\lucys\Desktop\WEATHER\weather_v2_denoms.mno` |
| size | **14440784** |
| sha256 (after fire) | `8dca67c5903453436c900ddc59446ce129bdacb473a070849902468bf26ab19b` |
| magic | `WEATHER1` |
| n_in / n_wire / n_gate / n_out | **8192 / 555412 / 555411 / 8192** |
| DEPTH | **22** |
| wavefront mean | **25245.955** = 555411/22 |
| n_rings / cells / ring0 | **6 / 32 / 104** |
| dests published | ring0@**104** = `1` · clock@**98** = `0` · carry@**168** = `0` · pub@**169** = `0` |
| fire | both senses cell 0, all 6 rings, `new=old\|0x01` · fwd/rev **0→1** |
| ones | **15606360** / 115526272 |
| computations/tick **(a)** | **25245.955** |
| ticks/second **(b)** | **1,000,000,000** |
| compute/second (a)×(b) | **2.5245955e13** |
| vs acre (a) | 20238.393→**25245.955** (**1.247×**) |
| vs shallow_acre (a) | 20966.125→**25245.955** (**1.204×**) by DEPTH 24→**22** |

Did not hit 28→14 (~40k). NAND2 XOR is DEPTH 3; two nested 8-bit prefix adds still serial. Open lane is still the denominator. This is the cut that verified byte-exact.

337 **NO** · pulsed_78 **NO** · invented_dest **NO** · acre smash **NO** · shallow smash **NO** · 10-wide **NO**
