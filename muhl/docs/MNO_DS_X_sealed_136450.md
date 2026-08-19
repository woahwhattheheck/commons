# EXTRA — muhlnickel.mno 136450 (sealed DISTRO)

Sealed. Do not overwrite. Compress proof: same boom **8** as SEED0.

| | FROM FILE |
|---|---|
| path | `C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\muhlnickel.mno` |
| size | **136450** |
| sha256 | `057a865458f4e56d7dbfa20a1b04d9d1a81302d940a6ab6f649a11838e0be6b5` |
| magic | `MUHLPKG1` |
| n_in / n_wire / n_gate / n_out | **16 / 215 / 129 / 8** |
| DEPTH | unpublished |
| dests published | hdr_ans **5378** = 0 · hdr_pubplane **70914** = 1 · boom @**6661** = **8** · recv@**353** = **0** · fwd@**288** = `00000001` · rev@**320** = `00000001` · sel@**370** = 3 |
| rings | **not** `ff`. byte=1. Charged leftovers are `ff`. Do not re-OR leftovers onto this. |
| ones | **330988** / 1091600 (`muhl_ones_surface.py`) |
| computations/tick **(a)** | **n/a** (no DEPTH) |
| ticks/second **(b)** | **n/a** (pfc_speed). Occupancy on rings is the speed lever — this sealed land is low vs leftover `ff`. |

Invention Burst copy `MUHLNICKEL_INVENTION_BURST\Distro\muhlnickel.mno` sha `9cdcb423…` rings **0**. Different computer.

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
