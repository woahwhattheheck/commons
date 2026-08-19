# DATASHEET 8 — weather_v2_acre.mno (NEW LAND)

**Inventor:** Bryce Muhlnickel. **When:** 2026-08-16 ~11:17pm. Fab + fire + surface.

Same KS cell as sheet 6. Field is **32×32** — four tiles of the 16×16 genesis. Size is not a throttle. Occupying disk **is** the computer sitting there. Critical-path DEPTH stays **28**. Wavefront scales with the parallel cells.

Quadrants are half-field (16×16), still 6 named rings, HIS nring2 formula. Does **not** smash v2 / ks / csa.

| | FROM FILE |
|---|---|
| path | `C:\Users\lucys\Desktop\WEATHER\weather_v2_acre.mno` |
| size | **14733648** |
| sha256 (after fire) | `ac284bde56d179dbb1ce286bd701798142b18330955bd9d48a8773cef479451c` |
| magic | `WEATHER1` |
| n_in / n_wire / n_gate / n_out | **8192 / 566676 / 566675 / 8192** |
| DEPTH | **28** |
| wavefront mean | **20238.393** = 566675/28 |
| n_rings / cells / ring0 | **6 / 32 / 104** |
| dests published | ring0@**104** = `1` · clock@**98** = `0` · carry@**168** = `0` · pub@**169** = `0` |
| fire | both senses cell 0, all 6 rings, `new=old\|0x01` · fwd/rev **0→1** |
| ones | **15911451** / 117869184 |
| computations/tick **(a)** | **20238.393** |
| ticks/second **(b)** | **1,000,000,000** |
| compute/second (a)×(b) | **2.0238393e13** |
| vs weather_v2 | (a) 2784.528→**20238.393** (**7.269×**) |
| vs ks 16×16 | same DEPTH 28 · (a) **3.992×** (4× cells, a little ring overhead) |

Verify same battery on the tiled field. Byte-exact vs `(N+S+E+W)>>2`.

337 **NO** · pulsed_78 **NO** · invented_dest **NO** · re-OR leftover **NO** · 10-wide **NO** · mmap_100gb **NO**
