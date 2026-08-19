# EXTRA — muhlnickel_dc.mno (unique dests, no 100GB mmap)

`muhl_surface_dc.py` published mouths only. mmap **NO**. 337 not fired. 7913 not lit. No inject.

| | FROM FILE |
|---|---|
| path | `C:\Users\lucys\Desktop\MUHL_DATACENTER\muhlnickel_dc.mno` |
| size | **99999999783** |
| magic | `MUHLDC01` (`4d55484c44433031`) |
| HEADER@0 | `MUHLDC01` |
| FOLD@224 | hex `0000040001000000` |
| carry@336 | `00000000` |
| pub@337 | `00000001` — **surfaced, not fired** |
| ring_fwd@524288 | hex `0100000000000000` |
| 7913_pub@524329 | `00000000` |
| computations/tick **(a)** | **n/a** — +8 IIII on this magic is not inspect layout (garbage n_gate). Do not invent. |
| ticks/second **(b)** | **n/a** |

Unique mouths the top 5 weather sheets do not have. Do not inject dc.

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
