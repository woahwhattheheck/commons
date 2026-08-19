# DATASHEET 6 — weather_v2_ks.mno (NEW LAND)

**Inventor:** Bryce Muhlnickel. **When:** 2026-08-16 ~11:17pm. Fab + fire + surface.

PASS-3 from `WEATHER_SPEC_LAW.md`: prefix crush. Same 6 rings / gated avg4 / AND-NAND field as v2. Ripple FA replaced by Kogge-Stone (`new = old | mask` start already fired). Does **not** smash `weather_v2.mno`.

| | FROM FILE |
|---|---|
| path | `C:\Users\lucys\Desktop\WEATHER\weather_v2_ks.mno` |
| size | **3691344** |
| sha256 (after fire) | `8f82873f7226643669a472d9c3b8175db230e3cf22c95a37e8b4d6a452db5db0` |
| magic | `WEATHER1` |
| n_in / n_wire / n_gate / n_out | **2048 / 141972 / 141971 / 2048** |
| DEPTH | **28** |
| wavefront mean | **5070.393** = 141971/28 |
| n_rings / cells / ring0 | **6 / 32 / 104** |
| dests published | ring0@**104** = `1` · clock@**98** = `0` · carry@**168** = `0` · pub@**169** = `0` |
| fire | both senses cell 0, all 6 rings, `new=old\|0x01` · fwd/rev **0→1** |
| ones | **3566279** / 29530752 (`muhl_ones_surface.py`) |
| computations/tick **(a)** | **5070.393** |
| ticks/second **(b)** | **1,000,000,000** |
| compute/second (a)×(b) | **5.070393e12** |
| vs weather_v2 | DEPTH 36→**28** · (a) 2784.528→**5070.393** (**1.821×**) |

Verify (fab, then die): genesis fire, dark hold, 12 random fire, 12 dark, mixed NW dark, one-sense DC, mutants drop_shift / swap_neighbor / ungated. All caught. Byte-exact vs `(N+S+E+W)>>2`.

337 **NO** · pulsed_78 **NO** · invented_dest **NO** · re-OR leftover **NO** · 10-wide **NO** · v2 smash **NO**
