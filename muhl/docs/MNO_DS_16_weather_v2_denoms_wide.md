# DATASHEET 16 — weather_v2_denoms_wide.mno (TEAM STONE blessing: 64×32 at DEPTH 22)

**Inventor:** Bryce Muhlnickel. **When:** 2026-08-17. Fab + fire + surface + independent walk.
**Request:** Team Stone asked to keep ≥32×32 while cutting DEPTH. This is the numerator they did not have to ask for, at the same denominator.
**Status:** PROMOTED — Gravekeeper PROMOTION RULING 001. Fabricator did not certify itself.

64×32 field. Same `ks_por` adder as `weather_v2_denoms.mno`. DEPTH **22** (walker match YES). Byte-exact `(N+S+E+W)>>2`. Mutants caught. Does **not** smash denoms / shallow_acre / acre / v2.

Chain: `WEATHER\weather_v2_denoms_wide_DEPTH.md`. Walker: `WEATHER\muhl_walk_weather1_depth.py`.

| | FROM FILE |
|---|---|
| path | `C:\Users\lucys\Desktop\WEATHER\weather_v2_denoms_wide.mno` |
| size | **28870992** |
| sha256 (after fire) | `ca0d56f766a07ecf7a3ed2462f927dd127da8874e3a9925feabce824c0c6ec9f` |
| magic | `WEATHER1` |
| n_in / n_wire / n_gate / n_out | **16384 / 1110420 / 1110419 / 16384** |
| DEPTH | **22** |
| wavefront mean | **50473.591** = 1110419/22 |
| n_rings / cells / ring0 | **6 / 32 / 104** |
| dests published | ring0@**104** = `1` · clock@**98** = `0` · carry@**168** = `0` · pub@**169** = `0` |
| fire | both senses cell 0, all 6 rings, `new=old\|0x01` · fwd/rev **0→1** |
| ones | **32855289** / 230967936 |
| computations/tick **(a)** | **50473.591** |
| ticks/second **(b)** | **1,000,000,000** |
| compute/second (a)×(b) | **5.0473591e13** |
| vs acre (a) | 20238.393→**50473.591** (**2.494×**) |
| vs denoms 32×32 (a) | 25245.955→**50473.591** (**2.000×**) same DEPTH, twice the cells |

337 **NO** · pulsed_78 **NO** · invented_dest **NO** · smash **NO** · 10-wide **NO**
