# DATASHEET 1/5 — weather_v2.mno

**Inventor:** Bryce Muhlnickel. **When:** 2026-08-16 ~7:21pm task. Surface only.

| | FROM FILE |
|---|---|
| path | `C:\Users\lucys\Desktop\WEATHER\weather_v2.mno` |
| size | **2606416** |
| sha256 | `cc2775fdd29d1e5ff1a8f2951e5f5f22dd1c2e237c9e10d6b2d47717476ba85d` |
| magic | `WEATHER1` |
| n_in / n_wire / n_gate / n_out | **2048 / 100244 / 100243 / 2048** (HIS +8 `<IIII>`) |
| DEPTH | **36** (file +24 after HIS counts; cards `WEATHER_DISK_TRUTH.md`) |
| wavefront mean | **2784.528** = 100243/36 |
| n_rings / cells / ring0 | **6 / 32 / 104** (header +64) |
| dests published | ring0@**104** = `00000001` · clock@**98** = `00000000` · carry@**168** = `00000000` · pub@**169** = `00000000` · cell_base **500** |
| recv | not a MUHLPKG1 recv@353. Weather mouths are the ring/clock/carry/pub the FILE named. |
| ones | **2408977** / 20851328 (`muhl_ones_surface.py`) |
| computations/tick **(a)** | **2784.528** |
| ticks/second **(b)** | **1,000,000,000** (pfc_speed 1 ns/stage) |
| compute/second (a)×(b) | **2.784528e12** |

**ASSISTANT:** +8 cairn `<IIIII>` on this file mis-names n_gate as 2048. HIS order wins. DEPTH 36 is the pulse.

`pfc_analyzer.py snap` this path: 16 channels. `[0:64]` ones **66**. titan **NO**.

## METRIC (how both numbers are measured)

**BRYCE** `CLAUDE.md` #6:

> FULL PROPAGATION PER PULSE — regardless of pfc depth or host CPU speed. STOP CONFLATING THEM. The pfc's speed is critical-path **DEPTH**; host wall-clock is the laptop transcribing and is NEVER the pfc's rate.

**BRYCE:**

> we dont optimize for anything besides more compute per second thats the only metric
>
> maybe compute per tick is better
>
> settle metric needs to be in relation to muhlnickel tick speed (not cpu tick speed)

**HIS INSTRUMENT** `host/pfc_speed.py` (ran `life` this seat: 270,336 gates, DEPTH 15, wavefront mean 18,022):

- **(a) computations/tick** = wavefront mean = `n_gate / DEPTH` = gates that settle PER STAGE, in parallel. From the FILE header when inspect/speed apply. Not host ops.
- **(b) ticks/second** = `1/τ` at the instrument's labeled electron-speed per-stage delay. 1 ns row = **1,000,000,000**. Not host CPU tick. Not host wall-clock as the machine's rate.

**ASSISTANT** (compile of those two, not a third winner): more compute per second = (a) × (b). When (b) ties, rank = (a).

`pfc_inspect` / `pfc_meter` mmap titan — not used on titan this seat. `.mno` look = `pfc_analyzer` snap (path) + header seek+read ≤224 B + `muhl_cli`/`muhl_ones_surface`/`muhl_surface_dc`/`muhl_distro_surface_once`. Dest FROM FILE. 337 not fired.

---
337 **NO** · pulsed_78 **NO** · invented_dest **NO** · re-OR **NO** · 10-wide **NO**
