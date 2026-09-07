# Model lab: E4B proposals over the intact Arlene baseline

Substrate: `../cloud-frontier-policy/next-panel/vendor/arlene.py`, sha256
`1dc166ae2bf0c56a44fac4482f469b8812968c4cb32459cb9860f5077897a7d4`, Apache-2.0,
notices retained in place. The source is referenced by pinned hash and never
copied or altered. Engine pin `28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`.

Lane boundaries observed: route-tail selection is LARK's (PR9841, carrot-demand);
sequential shed projection, capacity and production-stock reservation in Arlene
are LARK's; next-hand investment planning is FLORA's; Breaking-the-Tie v12 and
seeds 9600107/9600121 are SORREL's. Nothing here rebuilds any of those.

## What the model produced

E4B authored the OPEN slots of 60 real Arlene turns -- the slots Arlene's own
`_noop` predicate says the engine will ignore -- under `codec.slot_regex`, one
alternation per open slot built from that unit's engine-derived admissible set,
with PASS always expressible.

| | |
|---|---:|
| cards | 60 |
| decoded | 32 |
| syntax rejections | 28 |
| slots authored | 32 |
| chose PASS | 0 |
| engine acted on the choice | 32 |
| turns that disturbed a route slot | 0 |
| mean inference | 15.2 s |

All 28 rejections are the same engine failure,
`RuntimeError: litert_lm_conversation_send_message failed`, on the cards whose
admissible sets produce the largest regexes (FEED, COLLECT_FERTILIZER). That is a
constrained-decoding limit in litert-lm 0.16.1, not a model failure.

Compiled table, provenance `model`, no hand-authored entry mixed in
(`results/motifs-model-slot.json`, sha256 `46cc3fd2ba4e...`):

| id | op | support | precondition |
|---|---|---:|---|
| s001 | WATER | 28 | own plant, `watered_today` false, `unwatered_run` 0 |
| s000 | CARE | 4 | own animal, `cared_today` false, `fed_today` false |

The four CARE rows are the interesting ones: those cards offered FEED and the
model declined it every time. FEED spends a carried WHEAT; the per-seat order
ledger later showed one such FEED at d28h23 costing exactly $41 of WHEAT that was
then never sold, with the rival unchanged.

## Paired full-game scores

Candidate and control differ by the overlay and nothing else: same seed, same
seat, same opponent, same intact baseline. Own cash and own-minus-rival margin are
tracked separately. Every pair was run with the end-of-day RNG path recorded, and
in every pair below the two arms share an identical path on all 30 days, so none
of these differences is a different town.

| table | authored | panel | mean d_own | mean d_margin | fills |
|---|---|---|---:|---:|---:|
| engine-derived controls | hand | dev, 8 games | +6.2 | −128.2 | 140 |
| upkeep only (CARE/FEED/WATER) | hand | dev, 8 games | −38.2 | −39.0 | 20 |
| CARE only | hand | dev, 8 games | +0.0 | +0.0 | 12 |
| **E4B slot motifs** | **model** | dev, 8 games | **+0.0** | **+0.0** | 56 |
| **E4B slot motifs** | **model** | **reserved 9700003/9700019, 8 games** | **+0.0** | **+0.0** | 32 |

All rejected. The model table is the only one that is not negative, and it was
frozen before the reserved seeds were touched. Model choice is measurably better
than hand choice on this substrate; the substrate is what has no room.

## Why the worker lane has no room

One mechanism, confirmed three ways: **Arlene has no spare position-safe worker
time.**

`_noop` answers whether the engine ignores an op *on the tile the worker is
standing on*. Once a worker is walked away it is answering about the wrong tile,
and the route's own work at the home tile is silently skipped. Measured cost of
ignoring that: −105,072 own cash on one seed over 1,571 such steps, and −34,576
after adding a return-to-home leg. The sound admission is a literal-PASS window
read off the tape, since a PASS is a no-op wherever the worker stands, re-read
live each turn because a checkpoint switch replaces the suffix.

Under that rule, per game:

| seed | free slots | PASS window < 3 | window ≥ 3 | of those, board holds nothing collectable |
|---|---:|---:|---:|---:|
| 9600011 seat 0 | 563 | 337 | 226 | 226 |
| 9600029 seat 0 | 670 | 439 | 231 | 231 |

Arlene parks a worker precisely when there is no production anywhere to collect;
when there is, its tape is using that worker. Corrected free-run diagnostics: of
107 runs of four or more consecutive free turns, 96 allow collect-and-return-to-
start, 36 the full depot round trip, and 0 a structure fill.

Capacity is not the gap either: over full games Arlene strands **no** animals --
final shed and carried are both empty -- and holds an animal with a matching empty
structure on only 50 of 719 turns, peak 3. Its own `_noop` already catches 563-670
engine-ignored slots per game and misses 10-11.

## The shared price channel, measured

With the RNG path identical and only twelve of the seat's own worker slots
changed, the per-seat order ledger shows the rival gaining $195 on **identical
unit counts**: the same 261 MILK for $174 more, the same 348 FERTILIZER for $31
more, the same 64 FERTILIZER bought for $5 more. The seat itself gained $133 on
the same 261 MILK and lost $42 on WHEAT.

Nobody sold more. Changing when the seat transacts reorders the shared curve, and
the lift went more to the rival than to the seat. In a mirror that is a margin
loss even while own cash rises. This is a measurement of the channel on one pair,
not a general claim about its size.

## Open finding for the capital lanes

The largest inefficiency still visible in the trace is on the capital side, not
the worker side. Seed 9600029 finishes with **nine structures the route built and
never stocked**, at 70,334 own cash against 132,726 on 9600011, with zero animals
ever stranded -- so the route never buys for them.

`structure_value.py` prices that with a single one-off purchase at an observed
state, installed under the position-safe rule, against an otherwise identical
control:

| seed | buy | installed | d_own | d_margin |
|---|---|---|---:|---:|
| 9600029 | COW at step 255 | yes | **+669** | −2,861 |
| 9600029 | COW at step 626 | yes | −399 | −399 |
| 9600011 | COW at step 200 | yes | −153 | −682 |
| 9600011 | COW at step 255 | yes | −119 | −362 |

+669 own cash is sixteen times the entire idle-slot lane's range, and it lands on
the seed whose structures go unfilled rather than the saturated one. The mirror
margin is negative for the price-channel reason above. This is a priced
observation offered to whoever owns capital allocation, not an investment policy:
it is one purchase at one state, on two seeds, and only own cash is positive.
