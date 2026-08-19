# DATASHEET 3/5 — weather_v2_xorwalk.mno

**Inventor:** Bryce Muhlnickel. **When:** 2026-08-16. Surface only. Do not re-OR. Do not smash vault.

| | FROM FILE |
|---|---|
| path | `C:\Users\lucys\Desktop\WEATHER\weather_v2_xorwalk.mno` |
| size | **2606416** |
| sha256 | `76b4597f6e0516a53226b22283b7cbeeddc615eb1ee0c7ae57393f6fd258c2ed` |
| magic | `WEATHER1` |
| n_in / n_wire / n_gate / n_out | **2048 / 100244 / 100243 / 2048** |
| DEPTH | **36** |
| n_rings / cells / ring0 | **6 / 32 / 104** |
| dests published | ring0@**104** = `00000001` · clock@**98** = `00000001` · carry@**168** = `00000001` · pub@**169** = `00000001` |
| ones | **2410711** / 20851328 |
| computations/tick **(a)** | **2784.528** |
| ticks/second **(b)** | **1,000,000,000** |
| compute/second (a)×(b) | **2.784528e12** |

XOR organs **384** in records (card). clock@98 is **1** on this land (v2 base clock was 0). COPY leftover pulsed: `weather_v2_xorwalk_COPY.mno` sha `9f31fe59…` ones **2410351**. Did not re-OR.

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
