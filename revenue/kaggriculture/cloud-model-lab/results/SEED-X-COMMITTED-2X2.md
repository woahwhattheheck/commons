# Seed recovery × committed producer envelope: a 2×2 on one production parent

Two additive switches over a single intact selected parent. The production layer,
the parent call, the optimizer and the opponent are identical in all four arms, so
the arms differ only by which switches are on.

| arm | seed budget | capacity envelope |
|---|---|---|
| `baseline` | off | T08 `possible_extra_deposits`, the speculative upper bound |
| `seed` | **on** | T08 speculative |
| `committed` | off | **this producer's committed arrivals** |
| `combined` | **on** | **committed** |
| `bare` | off | T08 speculative, and **no cap production layer** — the intact parent, as an anchor |

`seed` is T13's `SeedBudget`, imported byte-identical from
`../cloud-hosted-loss-response/seed_budget.py`. `committed` is this lab's frozen
`committed_envelope.make_committed_sell`. T08's `conserved_sell_adapter`, the
frozen scheduler and intact Arlene are imported, never edited. Nothing in another
lane's tree is modified.

## Source pins

| file | sha256 | note |
|---|---|---|
| `cloud-hosted-loss-response/seed_budget.py` | `455024a4179a95ad597492e1f4b94de7bd3bfe7a3a88fd0dce46001f629ec3cd` | = T13 `SOURCE-FREEZE.json` |
| `cloud-titan-composition/vendor/sell/scheduler.py` | `32c8610c9827d1686a6f831e2c4b6af4c00d32d2aa04dcf25699d976d6d97dd9` | = T13 `SOURCE-FREEZE.json` |
| `cloud-titan-composition/conserved_sell_adapter.py` | `0df166b296b0f24e04620ae14c34031a5201c082da677f2c22005ce9d9d3ae4f` | T08, unmodified |
| `cloud-titan-composition/sell_adapter.py` | `81fc6050460efe4e943148abce7d60192690eb9a997c32c86d3156ffe7f80bc4` | T08, unmodified |
| `cloud-frontier-policy/next-panel/vendor/arlene.py` | `1dc166ae2bf0c56a44fac4482f469b8812968c4cb32459cb9860f5077897a7d4` | intact parent |
| `cloud-model-lab/committed_envelope.py` | `196770ca3ce1bb0d3ac7643282fd9c9da9fba866284ffddecaaa17957105b31a` | frozen, unchanged |

Engine pin `28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`. Public opponent bank from
PR9942, read-only from `cloud-policy-portfolio/revision2/vendor/opponents/`:
`lonespear-v18-greedy` source `eb5b5f59a8ec…`, `cok-v10` source `56831f3c43c9…`.

## Exactly one parent action, and who owns what

`PlanOverlay.act` calls intact Arlene once per turn; the SELL layer consumes that
already-selected action through T08's `SelectedAction` proxy, which raises if asked
for a second one. `post_units` is the engine's own deterministic unit stage on a
copy, not a policy call. The parent call is **counted**, not asserted.

```
farmer/hands slots   PlanOverlay cap overlay, only inside a literal-PASS tape window
market SELL slots    the SELL execution layer
market BUY_SEED      SeedBudget: reduction only, never an increase, index preserving
arrivals             PlanOverlay.producer_snapshot; the committed envelope is the
                     only consumer
```

## Compatibility and conservation, measured before any panel

T13's contract states its bound is derived from the intact Arlene/SELL route tape
and must not be stacked with an overlay that adds PLANT requests or rewrites
routes. `conserve.py` checks that precondition on real games rather than asserting
it, per turn of a 719-turn game.

| check | result |
|---|---|
| exactly one parent decision per turn | `{1: 719}` in every game |
| the cap overlay changes no PLANT request | 0 violations |
| the parent route table `R` is never mutated | 0 violations |
| the budget only reduces a BUY_SEED in place, never increases one | 0 violations |
| market slot count and index order preserved | 0 violations |
| SELL and the budget write the same slot on the same turn | 0 occurrences |

**A correction to the first cut of the last check.** It originally compared the
aggregate set of market indices each layer wrote across a whole game, and reported
a conflict on slots [1, 2]. The check was wrong, not the composition: slot 1 is a
SELL on one turn and a BUY_SEED on another, so an aggregate index overlap is not a
conflict. Re-cut per (step, slot) the answer is zero. The aggregate overlap is
still recorded, as information.

`compat_seed.py` answers the question T13's contract actually raises — does
stacking change the component's behaviour — by running the seed switch twice on
the same game, once over the bare intact parent and once over the cap-production
parent, and diffing `SeedBudget.events`.

| seed | seat | opponent | bare events | over production | cap fills | identical |
|---|---|---|---:|---:|---:|---|
| 9890019 | 0 | arlene | 2 | 2 | 11 | yes |
| 9890019 | 1 | arlene | 2 | 2 | 11 | yes |
| 9890040 | 0 | arlene | 2 | 2 | 11 | yes |
| 9890040 | 1 | arlene | 2 | 2 | 11 | yes |
| 9890043 | 0 | arlene | 2 | 2 | 11 | yes |
| 9890043 | 1 | arlene | 2 | 2 | 11 | yes |

6/6 byte-identical. So the co-firing seen below is not the overlay causing the
budget to fire.

## How often either switch fires at all

40 development games, seat 0 versus intact Arlene, seeds 9890040–9890079, all
running the combined arm. Zero conservation-check failures across all 40.

| | games |
|---|---:|
| the seed budget fired | 32 / 40 |
| the cap overlay fired | 28 / 40 |
| both fired | 28 |
| neither fired | 8 |
| the budget fired with the overlay silent | 4 |
| the overlay fired with the budget silent | **0** |

Firing is **bimodal**: the overlay fires either 11 times or not at all, the budget
either twice or not at all, with nothing in between. So additional seeds are not
independent evidence about *whether* these fire — only about *what a firing is
worth*. The overlay's firing set is a strict subset of the budget's; the budget
fires on four seeds where the overlay is silent, which is what rules out "the
overlay is what makes the budget fire" independently of the byte-identical event
logs above.

Non-firing seeds observed: 9890041, 9890049, 9890050, 9890062, 9890065, 9890070,
9890072, 9890075. 9890041 is carried into the panel below as a live null control.

## Development panel

4 seeds × 2 seats × 4 opponents = 32 cells, 5 arms, **160 games**, zero failures.
Seeds 9890019 / 9890040 / 9890043 (both switches fire) and 9890041, carried in as
a live null control. Opponents: intact Arlene, Apex, and the PR9942 public bank.

### Rating first

| arm | W/T/L | flips vs control | T→W | →L |
|---|---|---:|---:|---:|
| `baseline` | 32/0/0 | — | — | — |
| `seed` | 32/0/0 | **0** | 0 | 0 |
| `committed` | 32/0/0 | **0** | 0 | 0 |
| `combined` | 32/0/0 | **0** | 0 | 0 |
| `bare` | 32/0/0 | **0** | 0 | 0 |

**This panel demonstrates no rating change.** The control already wins every
development game, so there is no tie or loss available to convert, and no arm
turned a win into anything else. It bounds cash and risk; it does not show the
composition is stronger. Getting a rating signal needs a shard where the control
ties or loses — against Arlene the margins here are the closest (+808, +297,
+696), and nothing moved them.

### Cash, which diagnoses why — not the result

| arm | mean d_own | mean d_rival | mean d_margin |
|---|---:|---:|---:|
| `seed` | +187.5 | +0.0 | +187.5 |
| `committed` | +276.0 | +20.1 | +255.9 |
| `combined` | **+463.5** | +20.1 | +443.4 |
| `bare` | −49.6 | +0.0 | −49.6 |

`bare` at −49.6 is the cap production layer's own contribution: dropping it costs
about 50 own cash on average, so the production overlay is mildly positive and the
two switches are what carry the panel.

Part of the committed envelope's cash is **not** taken from the rival: mean rival
delta is +20.1, so the release of capacity moves the shared book for both seats,
not only for this one. That is the same shared price channel measured in
`MODEL-LAB-RESULTS.md`, and it is why margin (+443.4) is below own cash (+463.5).

### The two switches are exactly additive here

`d(combined) − d(seed) − d(committed)`, own cash, over all 32 pairs:
**min +0, max +0, nonzero pairs 0.** Not approximately additive — identically.

That is consistent with, and independently supported by, the compatibility
evidence above: disjoint write sets, an untouched route tape, and byte-identical
budget event logs with and without the production layer. It is a measurement on
32 pairs of one shard, not a general claim that these two switches commute.

### Every pair is the same market world

All 128 arm games share the control's end-of-day RNG path on all 30 days —
**0 divergent pairs**. No cash difference in this panel is a different town.

### Worst single action

162 ms across every arm and game, cold first call included, well inside the
one-second-per-action environment contract.

### What the counts really are

Game counts overstate the evidence, so the true independent counts:

| | reported | real |
|---|---:|---:|
| control outcomes | 32 | **20** |
| opponent entries / lineages | 4 | **3** |
| non-discriminating cells (rival finished on 0 cash) | — | 4 |

Both seats return byte-identical cash in **12 of 16** (seed, opponent) cells, so
those seats are one observation and not two. lonespear and COK are two frozen
public source revisions from ONE bank, not two independent opponent families.
COK finishes on zero cash whenever it plays seat 0's rival, and those four cells
are wins in every arm regardless of the switches — they are a runtime and
compatibility check, not evidence of playing strength. This matches T07's own
smoke, in which all 12 public-bank games were losses.

A firing correction from this panel: 9890041 was classified non-firing by the
census, which only ran seat 0 versus Arlene. It is indeed inert versus Arlene and
Apex — every arm +0, which is the null control working — but the budget **does**
fire on it versus lonespear (+240). Firing is a property of (seed, seat,
opponent), not of the seed.

## Cross-check against T08's shipping default

Independent of the 2×2, T08's selected arm (`arms/sell.py`, frozen SELL) was run
against its own conserved cap composition (`arms/carrot_cap_sell_conserved.py`)
on the new public bank — a pairing nobody had run, since the bank landed after
T08's panels. `execute_arm.py`, 16 games, 0 failures, both 8/0/0.

| seed | seat | opponent | frozen SELL own | conserved own | d_own | RNG path |
|---|---:|---|---:|---:|---:|---|
| 9890019 | 0 | lonespear | 94,619 | 94,464 | −155 | identical |
| 9890019 | 0 | COK | 167,694 | 166,794 | −900 | identical |
| 9890019 | 1 | lonespear | 94,619 | 94,464 | −155 | identical |
| 9890019 | 1 | COK | 77,887 | 77,691 | −196 | identical |
| 9890040 | 0 | lonespear | 154,692 | 154,685 | −7 | identical |
| 9890040 | 0 | COK | 125,136 | 122,730 | −2,406 | identical |
| 9890040 | 1 | lonespear | 154,692 | 154,685 | −7 | identical |
| 9890040 | 1 | COK | 87,890 | 88,977 | +1,087 | **2 divergent days** |

Worst action: frozen SELL 124.7 ms, conserved 170.5 ms.

The last row is the one to discount: its end-of-day RNG path diverges on two
days, so +1,087 is not a like-for-like comparison — that pair is a different
town, and it is the only such pair in the whole run.

This makes the committed envelope's effect concrete rather than statistical. On
9890019 seat 0 my `baseline` scores 94,464 versus lonespear — byte-identical to
T08's conserved arm — and `committed` scores exactly 94,619, which is frozen
SELL's own figure. Versus COK the same seed: baseline 166,794, committed +900 =
167,694, again exactly frozen SELL. **On these cells the committed envelope
recovers precisely the cash the speculative envelope costs the cap composition**,
while keeping the cap production. That is the specific quantity the earlier fixed
-state ablation predicted would be at stake, measured here on whole games.
