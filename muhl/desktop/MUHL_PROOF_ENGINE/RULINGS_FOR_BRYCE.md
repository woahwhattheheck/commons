<!-- AUTHORSHIP: written by an AI assistant at the owner's instruction. Not the owner's writing. -->

# TWO RULINGS — brought to you, 2026-08-06

You said: **"bring them to me"**. Here they are with the evidence recomputed live from
`titan_circuits.json`, not repeated from a prior session's doc. Everything below is a
STRUCTURAL fact (registry offsets, lengths, recorded depths) — the kind that holds regardless
of byte movement, so it is safe to state. No verdict is offered on either.

---

# RULING 1 — `muhl_lane_bank_002` and `muhl_fold_phys`

## The previous write-up said "overlap". The live registry says something sharper.

    muhl_lane_bank_002    [1,115,398,576 , 1,219,807,207)    len = 104,408,631
    muhl_fold_phys        [1,128,237,250 , 1,142,298,816)    len =  14,061,566
    muhl_fold_phys_wires  [1,127,673,856 , 1,128,237,250)    len =     563,394

**`muhl_fold_phys` is not partially overlapping `muhl_lane_bank_002`. It sits ENTIRELY INSIDE
it.** Its start is 12,838,674 B past `_002`'s start, and its end is 77,508,391 B before `_002`'s
end. The overlap of **14,061,566 bytes is exactly `muhl_fold_phys`'s whole length** — recomputed
live, and it matches your documented figure to the byte.

`muhl_fold_phys_wires` sits immediately before it and is *also* fully inside `_002`'s span. So
the fold and its wires together are nested within the lane bank's declared territory.

This is not "two circuits arguing over a contested strip." It is **one circuit allocated wholly
inside another's declared range.**

## What each one is

| | `muhl_lane_bank_002` | `muhl_fold_phys` |
|---|---|---|
| format | `typed` / `PFCWINMN` | `physical-address` / `MUHLFLD1` |
| gates | 11,600,487 | 562,462 |
| depth | *none recorded* | **3,243 ticks** |
| rating | *none recorded* | — |
| referenced by | 1 entry (`muhl_allocator`) | 3 entries (`latch_reg`, `muhl_fold_latch`, `muhl_lane_bank_002`) |

`muhl_fold_phys` at DEPTH **3,243** is the LEVERED fold — your own CLAUDE.md records the fold
going **11,757 → 3,243 ticks (3.63×) with 27,797 dead gates pruned to zero.** It is addressable,
it has three dependents, and it is one of the measured wins in the corpus.

`muhl_lane_bank_002` is still in the old typed format, has no recorded depth or rating, and is
referenced only by `muhl_allocator` — which references it as the *example of the failure the
allocator exists to prevent*.

## The question, and only you can answer it

**Which circuit owns bytes [1,128,237,250 , 1,142,298,816)?**

I will not guess, because reading `_002`'s gate table through its own 9-byte/5-opcode lens
across that region yields records that are actually `muhl_fold_phys`'s bytes. Rebuilding either
circuit from that region without your ruling would fabricate a circuit from a guess — the
substitution failure.

`muhl_allocator` (944 gates, DEPTH 74, monotone high-water) is the structural fix and is live,
so this cannot recur. This is about the one pre-existing case.

---

# RULING 2 — does the substrate settle a TYPED gate in one tick?

## The measurement, re-confirmed live

| circuit | recorded TYPED depth | NAND-rebuild depth | ratio |
|---|--:|--:|--:|
| `muhl_lateral_fold` | 11,756 | 25,161 | **2.14×** |
| `muhl_mid` | 1,441 | 3,097 | **2.15×** |

Your opcode table, from your own `host/fab_genwin_shared.py:35`:
`CODE = {"nand":0, "and":1, "or":2, "xor":3, "not":4}`

Expressed in NAND: `nand`/`not` are 1 level, `and` 2, `or` 2, `xor` 3. A typed netlist counted
one-level-per-gate therefore reads ~2.15× shallower than the same logic counted in NAND.

## Why it matters

Your one metric is **compute/tick = REPLICAS / DEPTH**. DEPTH is the denominator, so a depth
that is 2.15× too small makes the rating 2.15× too large.

## Current scope — smaller than the earlier doc said

The previous write-up said 81 typed circuits. Live registry now:

- **8** `PFCWINMN` entries remain in typed form — all `muhl_lane_bank_00*`, each recording
  **depth 2,892** and no rating.
- **103** `MUHLPHY3` rebuilds exist alongside their typed originals.

So the ruling now governs the 8 remaining typed lane banks' recorded depths, and whether the
103 rebuilds' NAND depths or their originals' typed depths are the figure of record.

## The question, and only you can answer it

**Does the substrate settle a typed AND / OR / XOR in ONE tick, or does it settle NAND-only?**

- **Typed settles in one tick** → the recorded depths are right, decomposition is the
  pessimistic representation, and the correct rebuild PRESERVES the opcode in the physical
  `<BQQQ>` record. The format already carries an op byte, so that is buildable with no format
  change.
- **NAND-only** → the typed depths are ~2.15× optimistic and should be re-derived, and
  decomposition is the correct rebuild.

Nothing has been altered either way. Originals are untouched, every rebuild is journaled and
byte-exact revertible, and no recorded depth or rating has been edited.
