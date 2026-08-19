# EXTRA — loom.mno (unique dest)

| | FROM FILE |
|---|---|
| path | `C:\Users\lucys\Desktop\MUHLNICKEL_LOOM\loom.mno` |
| size | **140454** |
| sha256 | `7356173b5000a719dacf343dd7a0ab18e4b7a04e0c387b772e1d8a0246e6659a` |
| magic | `LOOMPKG1` |
| n_in / n_wire / n_gate / n_out | **16 / 369 / 283 / 8** |
| DEPTH | unpublished |
| dests published | hdr_ans **9382** = 193 (`11000001`) · pubplane **74918** = 1 · boom ans+1283 @**10665** = **10** · recv@**353** = 0 · fwd/rev @288/@320 = 1 · sel@**370** = 17 |
| computations/tick **(a)** | **n/a** (no DEPTH) |
| ticks/second **(b)** | **n/a** |

Unique dest **9382 / 10665** — not 6661. twins: LOOM_fixed / v1 / v2 same size, different sha/rings. Do not invent dest.

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
