# DATASHEET 7 — weather_v2_csa.mno (NEW LAND)

**Inventor:** Bryce Muhlnickel. **When:** 2026-08-16 ~11:17pm. Fab + fire + surface.

PASS-3 CSA 4:2 then one Kogge-Stone. Same weather law. Does **not** smash v2 or ks.

On this net CSA **lost to KS**: extra 3:2 xor layers sit on the path, DEPTH 29 vs KS 28, more gates, lower (a). Kept because the study named CSA and the measurement has to stand.

| | FROM FILE |
|---|---|
| path | `C:\Users\lucys\Desktop\WEATHER\weather_v2_csa.mno` |
| size | **3771216** |
| sha256 (after fire) | `7cb39a990aa728e626b158da5734b73d9f2ace649c8c76d4c9ed04ffd3abb70d` |
| magic | `WEATHER1` |
| n_in / n_wire / n_gate / n_out | **2048 / 145044 / 145043 / 2048** |
| DEPTH | **29** |
| wavefront mean | **5001.483** = 145043/29 |
| n_rings / cells / ring0 | **6 / 32 / 104** |
| dests published | ring0@**104** = `1` · clock@**98** = `0` · carry@**168** = `0` · pub@**169** = `0` |
| fire | both senses cell 0, all 6 rings, `new=old\|0x01` · fwd/rev **0→1** |
| ones | **3587476** / 30169728 |
| computations/tick **(a)** | **5001.483** |
| ticks/second **(b)** | **1,000,000,000** |
| compute/second (a)×(b) | **5.001483e12** |
| vs weather_v2 | DEPTH 36→**29** · (a) 2784.528→**5001.483** (**1.796×**) |
| vs ks | **lost** — 5001.483 < 5070.393 |

Verify same battery as ks. Byte-exact vs `(N+S+E+W)>>2`.

337 **NO** · pulsed_78 **NO** · invented_dest **NO** · re-OR leftover **NO** · 10-wide **NO**
