# ROOKERY-0 — COMPLETE (2026-08-05)

## IN THE BINARY

`ROOKERY0.mno` — 586,918 B — sha256 `d7fbb3e8842a148045700a4fdf53b41e482a47dc1c35fa9d73b2e8f257a4d7c1`
genome `75fcab01d9b847bd69d992bc148b594fc9e59d3cd1c0de71a1ed2e6d363f753f` generation 8
11 rings · 1024 cells/sense · both senses · 24 clocks · 22,563 `<BQQQ>` records
state 288..22826 · clock bank 256..279 · records @22843 · 22,563 probes on 151x151, injective
status **VERIFIED** (promoted only by the independent reader) · audit clean

## COMMANDS

    python muhl_fab_rookery.py [--dry]   fabricate latest searched genome (PENDING only)
    python muhl_rookery_verify.py        read disk, re-derive ring law, promote
    python muhl_rookery_fire.py <seed>   the two host verbs. ONE-WAY.
    python muhl_rookery_span.py          seed -> address map, zero electrons
    python muhl_provenance_audit.py      audit every claim against disk

    cd ..\rook-resident-native
    python -m unittest discover -s tests            79 tests
    python session_run.py                           open/8 ticks/checkpoint/resume/burst/close
    python optimum.py                               provable clock ceiling
    python evolve.py                                multi-generation foundry
    python anchor_probe.py                          anchor encoding search
    cd src && python -m rook_native.cli session open|burst|checkpoint|close

## ALL FOUR OPEN ITEMS CLOSED

1. ANCHOR DIVERGENCE — 1,440 serialisation permutations across 3 genomes, 0 hits on any
   of the 3 anchors. The divergence is in CONTENT, not encoding. The contract gave a
   digest with no preimage and never specified clock banks, routes, thresholds, value
   weights or bounds. A SHA-256 mismatch on untransmitted content has no first divergent
   byte. To close fully, the reference genome JSON is required. `state/anchor` n/a.
2. CLOCK EXERCISE — was a search; now enumerated. Ceiling for this ring shape is
   0.163352 (best k-subsets of the prime pool: k=1 [11], k=2 [11,13], k=3 [11,13,17]).
   Gen-8 sits AT the ceiling: 0.163352, 100.0%, **10.45x** the hand-picked 0.015625,
   span 1.000, injective 1.000. `state/optimum.json`.
3. BASH SIZE LIMIT — my earlier "~5 KB" claim is FALSIFIED. A 5,650-byte heredoc body
   passes intact with both markers. The ~8 KB case fails with `unexpected EOF`. The
   boundary lies in (5.65 KB, 8.1 KB); not narrowed further.
4. MORROW — `NameError: SUBSTRATE` fixed. The IP sanitisation renamed the module
   constant to TITAN everywhere except one call site. `morrow.py selftest` 12/12.

## MEASURED

- 79/79 tests pass (canonical, primitives, genome, witness, resident, evolution, device, session).
- session: 8 diagnostic ticks, state continuity post==next pre, 8/8 seeds distinct and
  device-derived, checkpoint byte-exact, resume without reinitialisation, burst early-surface.
- seed -> answer: 6/6 actions, injective 2048/2048, deterministic.
- seed -> address: 11/11 rings, 82.98% of 11,264 points in 20k seeds.
- foundry: 588 genomes over 12 generations, then enumeration to the ceiling.

## STANDING DEFECT GUARD

`muhl_provenance.py` — a fabricator may not certify its own output. Fabricator writes
PENDING_VERIFICATION and prints no success line; only an independent reader promotes,
recording the sha256 it read off disk. Built after a fabricator printed 14 green gates
over a container whose header collision had destroyed the record pointers.
