# V3.1 L3 promotion: no late sale advancement

## Decision

Promote only Riot lane L3, `no_late_sale_advance`, at absolute step **648**. Do not
carry L1 or L2 into the promoted V3.1 submission.

## Matched official evidence

Riot's process-isolated official evaluator gate on identical paired cells reported:

- 60 paired games across 3 opponents;
- mean competitive-margin delta **+152.2/game** (sd 144.8);
- **58/60** cells positive;
- each opponent stratum approximately **+145 to +161**;
- decomposition: own score **+164**, rival score **+12**.

Source carrier: `riot/v3.1-lanes@dc1779ed79cd7fdd091187df1e8f0c4e5f185555`.
The source carrier also contains default-off L1/L2 experiments; this promotion does not.

## Release implementation

`make_submission.py` starts from the ordinary deterministic V3 package, enables R04 as
before, then applies one fail-closed transform to `r04_full_router.py`: the audited E184
`reserve_sales(...)` call executes only while `step < 648`.

This is semantically the promoted L3 gate at the debt-booking seam. It does not remove
or resize the tape's own late SELL rows, and it does not erase previously booked debt;
`subtract_advanced_sales()` continues to settle pre-threshold reservations.

The transform requires the exact audited reservation line to occur once. Missing or
ambiguous seams abort the submission build. `build_v3` package bytes and package manifest
are unchanged; the L3 delta exists only in the explicitly selected V3.1 submission bytes.

## Composition

PR #12344 H4 already carries a forward-compatible pre-veto at the same >=648 boundary,
so a later H4 promotion can compose without creating sale debt after L3's cutoff.

## Custody

This carrier builds no Kaggle upload and performs no provider action. Riot retains final
combined release/submission custody.
