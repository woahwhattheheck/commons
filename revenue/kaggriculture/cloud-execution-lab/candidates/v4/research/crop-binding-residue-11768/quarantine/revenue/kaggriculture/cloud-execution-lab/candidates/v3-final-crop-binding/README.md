# TITAN V3 final crop-binding candidate

Operations:

- parent: `op:titan-v3-final-crop-binding-20260909-01`
- residue follow-up: `op:titan-v3-crop-binding-residue-20260909-02`

## Defect

The enabled crop-release path creates receipt-critical market edits in
`SpatialTempo.crop_market()`:

- an appended `BUY_PRODUCT WHEAT` lot, or
- exact-index reductions of existing `SELL WHEAT` lots.

`TitanAgent._finish_production()` currently calls
`guard_crop_returned()` before `_early_capital_selected()`. The canonical
entrypoint then uses that early-capital seam to apply final market pressure.
Those late transforms may reorder the exact rows after the guard has accepted
them.

`commit_input_repair()` correctly refuses to attribute a receipt to a changed
queue. If the WHEAT buy or changed sale rows remain executable, it marks
`input_repair_unknown`; future repair is then suppressed to avoid duplicate
purchases. The result is legal gameplay but stranded crop-recovery state.

## Candidate

`FinalCropBindingAgent` grants queue ownership only when the proposal remains
exactly bound after `guard_returned()` and the selected post-unit snapshot.
That exact owner suppresses feed-stock, early-capital and final-pressure edits
until the final binding guard and receipt commit.

A deadline fallback or unit guard can leave a timed-stage proposal attached to
an action that no longer contains or binds it. The candidate first asks the
canonical crop guard to remove or restore recognizable repair effects, then
detaches the proposal before late market transforms. It restores the proposal
only for `commit_input_repair()` so any unremovable WHEAT buy or altered sale
slot is still classified `input_repair_unknown`. Clearing the proposal
permanently would be fail-open: the residue could execute while a later turn
issues a duplicate repair.

Ordinary or retired-proposal decisions retain:

`feed stock -> early capital -> final pressure -> receipt commits`

Exactly bound crop-repair decisions use:

`repair-owned queue -> final binding guard -> receipt commits`

No route, quantity, product choice, feature default, canonical source, archive,
release pointer, provider or Kaggle state is changed by this candidate.

## Acceptance

The focused suite has ten contracts covering:

1. predecessor finalizer ordering;
2. the real early-capital stable sort that poisons an already accepted repair;
3. exact final-queue binding to `input_repair_pending`;
4. WHEAT-sale withholding index ownership;
5. validated suppression of feed, capital and pressure;
6. rejection of raw stale-proposal ownership;
7. deadline-after-proposal retirement;
8. post-guard unit-mismatch cancellation;
9. fail-closed classification of an unremovable repair residue; and
10. lifecycle cleanup of the validated ownership and proposal flags.

Run from the candidate directory with the lab on `PYTHONPATH`:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="../..:." \
  python -m unittest -v test_final_crop_binding.py
```

This is a source-correctness challenger. Full matched official-engine games,
not these contracts, decide playing-strength promotion.
