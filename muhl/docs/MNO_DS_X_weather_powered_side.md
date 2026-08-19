# EXTRA — weather_powered_side.mno (next cpt, unique n_gate/DEPTH)

Not in the top-5 tie. Unique circuit counts the v2 sheets do not have.

| | FROM FILE |
|---|---|
| path | `C:\Users\lucys\Desktop\WEATHER\weather_powered_side.mno` |
| size | **2726822** |
| sha256 | `85a53bfa7bd0a497c5cd7fc9cd7d5ae375e2043cc06a29febc0eed6e32765423` |
| magic | `WEATHER1` |
| n_gate / DEPTH | **104874 / 40** |
| computations/tick **(a)** | **2621.850** |
| ticks/second **(b)** | **1,000,000,000** |
| ones | **2502274** / 21814576 |

Rank by (a): after the v2 tie, this is next. v1 class is **116.603** (n_gate 34048 DEPTH 292).

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
