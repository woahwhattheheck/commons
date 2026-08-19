# EXTRA — SEED0 / ACREAGE charged leftover (do not re-OR)

Leftover legal. Already charged `old|mask`. **Do not re-OR.**

| | FROM FILE this seat |
|---|---|
| path (look) | `C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\SEED0.mno` |
| size | **8192** |
| sha256 | `faa70efc328e9b596eb27d6c1b2e2c4d76a863d8a81380f0d22ec7a8e4d85071` |
| magic | `MUHLPKG1` |
| n_in / n_wire / n_gate / n_out | **16 / 215 / 129 / 8** |
| DEPTH | unpublished |
| dests | boom @**6661** = **8** · recv@**353** = **1** · rings @288/@320 **`11111111`** |
| ones (card) | **10413** — ACREAGE / ACREAGE_COPY / SEED0 / slot_0 (look) same sha |
| computations/tick **(a)** | **n/a** |
| ticks/second **(b)** | **n/a** as pfc_speed. Rings `ff` = occupancy lever vs sealed DISTRO rings=1. |

Other leftover classes (do not re-OR): GERM/NEW_MNO/slot_4 sha `717248b1…` ones **8914** · MOVE sha `852c4289…` ones **10276** · VIRGIN/N2/SEED0_COPY/MIRROR sha `9aa0855f…`.

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
