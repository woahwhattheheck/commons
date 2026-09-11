# D5 — public tight-cash risk dial (experiment only)

This directory is a **default-OFF research carrier** stacked on the exact L3
source head from PR #12377 (`d181d6ecf848f88885bc1cc348c456714b7360cd`).
It changes no `overlay/**` file, package input, manifest, evaluator, opponent,
submission, or Kaggle artifact.

## Question

Unconditional L3 (late E184 sale-advance suppression) has a real but
opponent-sensitive economic effect. D5 asks a narrower question: can the same
already-existing suppression seam be used only when the live game is publicly
close enough that taking the risk is useful?

The first source-safe proxy is the absolute gap between the two farms' current
public `money` fields at the **literal L3 latch step 648**. Classification is
one-shot and latched for the remainder of that player's episode so the candidate
cannot switch arms because its own later market choices changed cash. If step
648 is malformed or skipped, that player remains guarded for the rest of the
episode; a later 649/700 callback may not classify. Player state is isolated, so
malformed input for one seat cannot erase the other seat's established latch.

The pinned official engine initializes farm money as `float(starting_money)` and
moves it with integer-priced game transactions. D5 therefore treats an exact
finite **integral** float such as `3000.0` as the same public money value as
`3000`, normalizing it without rounding. Bool values, numeric strings,
non-integral floats, NaN, and infinities fail closed. Step, player, latch step,
and threshold remain strict non-bool integers.

This is **not** a claim that cash gap equals score gap or net-worth gap. It is a
public, contemporaneous development proxy only. The candidate does not inspect
rival shed/inventory/orders, private observations, replay outcome, evaluator
scores, or opponent identity.

## Exact mutation boundary

The candidate temporarily gates only `r04_no_late_sale_advance.suppressed()`.

- tight arm: the existing #12377 L3 suppression may run;
- guarded arm: baseline E184 `reserve_sales()` remains enabled;
- no worker command, market quantity, row order, debt record, tape, production
  choice, or terminal liquidation is directly rewritten by D5;
- malformed, skipped, or ambiguous latch state fails closed to baseline E184.

## Screening parameter — no promotion authority

`DEFAULT_MAX_ABS_CASH_GAP = 5000` is an explicit **development screening
constant**, not a selected or promoted threshold. Do not infer economics from
its presence in source. A real gate must sweep or otherwise rebind the cutoff
under the exact materialized V3.1 package and pinned official interpreter.

A threshold is eligible for further consideration only with paired evidence
that reports, per cell:

- candidate seat and exact opponent fingerprint;
- `cash_gap` captured at the literal latch step;
- guarded vs suppressed late decisions;
- candidate and control own score, rival score, and competitive margin;
- `Δown`, `Δrival`, and `Δmargin` (D3 externality screen);
- every negative transition, not just the mean.

Reject a cutoff that merely shifts value to the rival, rescues one opponent by
creating new losses elsewhere, or derives its apparent benefit from a
non-1:1/package-fidelity harness.

## Focused source checks

Run from this directory:

```bash
python3 -B -m unittest -v test_candidate.py
python3 -O -B -m unittest -v test_candidate.py
```

The predecessor suite binds the pinned engine's public-money float contract and
covers public-cash symmetry; exact integral-float reachability; bool/string/
fractional/nonfinite money rejection; exact two-player farm shape;
before/at/after exact-latch behavior; inclusive cutoff semantics;
treatment/control latching; rewind/reset; malformed-648 permanent guard;
skipped-648 permanent guard; first-callback-after-648 guard; interleaved-seat
isolation; parameter typing; guarded/allowed L3 call-site behavior;
preservation of L3 telemetry; disabled/pre-threshold identity; and malformed
predicate inputs.
