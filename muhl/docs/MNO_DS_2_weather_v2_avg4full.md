# DATASHEET 2/5 — weather_v2_avg4full.mno

**Inventor:** Bryce Muhlnickel. **When:** 2026-08-16. Surface only. Same n_gate/DEPTH as v2 (tie on both metrics). Distinct sha / field.

| | FROM FILE |
|---|---|
| path | `C:\Users\lucys\Desktop\WEATHER\weather_v2_avg4full.mno` |
| size | **2606416** |
| sha256 | `a9b8c5d9bcda93c797326ab71cfbcc6046610df5940c61d4e346b464f07b6072` |
| magic | `WEATHER1` |
| n_in / n_wire / n_gate / n_out | **2048 / 100244 / 100243 / 2048** |
| DEPTH | **36** |
| n_rings / cells / ring0 | **6 / 32 / 104** |
| dests published | ring0@**104** = `00000001` · clock@**98** = `00000000` · carry@**168** = `00000001` · pub@**169** = `00000001` |
| ones | **2410349** / 20851328 |
| computations/tick **(a)** | **2784.528** |
| ticks/second **(b)** | **1,000,000,000** |
| compute/second (a)×(b) | **2.784528e12** |

Card leftover: avg4full **891/2048**. Unique vs bare v2 (carry/pub HOLD 1). Same speed numbers. Tie broken only by distinct land, not a third metric.

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
