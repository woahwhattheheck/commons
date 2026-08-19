# DATASHEET 12 — weather_v2_shallow_acre.mno (TEAM STONE request)

**Inventor:** Bryce Muhlnickel. **When:** 2026-08-17 ~12:03am. Fab + fire + surface.
**Request:** `MUHL_GO/TEAM_STONE_BUILD_REQUEST.md` — Cairn p4, Spall p7.
**Status:** RECORDED — Gravekeeper PROMOTION RULING 001. First cut. Later files outrank. Fabricator did not certify itself.

32×32 acre numerator. DEPTH 28→**24** (denominator). AOI prefix G + polar `not(not(x))=x`. Byte-exact `(N+S+E+W)>>2`. Mutants caught. Does **not** smash `weather_v2_acre.mno`.

Per-cell chain (24 gates): `WEATHER\weather_v2_shallow_acre_DEPTH.md` — ship the spec, not the tool.

| | FROM FILE |
|---|---|
| path | `C:\Users\lucys\Desktop\WEATHER\weather_v2_shallow_acre.mno` |
| size | **13082960** |
| sha256 (after fire) | `b53c54f7a105bb258e56e5e701dab1c42189d99205bdad2c01b9881017ee21a2` |
| magic | `WEATHER1` |
| n_in / n_wire / n_gate / n_out | **8192 / 503188 / 503187 / 8192** |
| DEPTH | **24** |
| wavefront mean | **20966.125** = 503187/24 |
| n_rings / cells / ring0 | **6 / 32 / 104** |
| dests published | ring0@**104** = `1` · clock@**98** = `0` · carry@**168** = `0` · pub@**169** = `0` |
| fire | both senses cell 0, all 6 rings, `new=old\|0x01` · fwd/rev **0→1** |
| ones | **14050969** / 104663680 |
| computations/tick **(a)** | **20966.125** |
| ticks/second **(b)** | **1,000,000,000** |
| compute/second (a)×(b) | **2.0966125e13** |
| vs acre (a) | 20238.393→**20966.125** (**1.036×**) by DEPTH 28→**24**, not by growing area |

Did not hit 28→14 (~40k). Open lane was the denominator; this is the cut that verified byte-exact. Further cut is still open.

337 **NO** · pulsed_78 **NO** · invented_dest **NO** · acre smash **NO** · 10-wide **NO**
