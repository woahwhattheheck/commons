# SOL-TAILGUARD — paired-cell tail admission

Operation: `TITAN-V3-PAIRED-CELL-TAIL-ADMISSION-20260910-01`

## Why this exists

A pooled panel can report positive mean TITAN cash, nonnegative median cash,
more positive than negative cells, positive mean margin, and zero new losses,
yet still hide a catastrophic matched-cell TITAN regression. The failure is
especially deceptive when the rival loses even more cash: relative margin rises
while TITAN's own terminal bank falls.

The live V1/V2 structural-core investigation exposed exactly this selection
hazard. The inherited bound-panel gate reports useful aggregate and
opponent-by-seat statistics, but those are not a per-cell tail floor.

## Contract

`paired_cell_tail_admission.py` ignores every upstream claimed delta and verdict.
It re-derives terminal own cash, rival cash, margin, and outcomes from each
matched control/candidate pair. It fails closed on:

- duplicate, missing, incomplete, or mismatched cells;
- evaluator or optional panel-descriptor drift;
- non-finite scores or scores detached from terminal bank snapshots;
- incomplete 720/719 lifecycles;
- malformed returned-action or trace digests;
- trace or terminal-score drift without returned-action activation.

For an active candidate, `ADMIT` requires all of the following:

1. at least one returned-action hash changes;
2. TITAN own-cash delta is nonnegative in **every** changed cell;
3. TITAN own cash is strictly higher in at least one changed cell;
4. margin delta is nonnegative in **every** changed cell;
5. there are zero new losses; and
6. there are zero lost wins.

Exact action parity returns `INACTIVE`. Any active failure returns `REJECT`.
The receipt includes every re-derived cell, opponent×seat and seed aggregates,
explicit regression rows, deterministic binding hashes, and a self-excluding
receipt seal.

This module is deliberately the *tail* layer, not a replacement for upstream
source custody. Exact archive, engine, evaluator-patch, seed-ledger, and
action-capture provenance must already be established by the producing
panel. The gate binds control and candidate to the same reported evaluator
and immutable descriptors, then independently verifies the cellwise score
frontier.

## Adversarial predecessor

`MECHANISM-WITNESS.json` contains eight matched cells. Seven gain TITAN +10.
The eighth remains a win and gains margin because the rival falls from 90 to 0,
but TITAN falls from 100 to 50. The pooled evidence is deliberately seductive:

- mean TITAN cash delta: +2.5;
- median TITAN cash delta: +10;
- positive/negative cells: 7/1;
- mean margin delta: positive;
- new losses: 0;
- lost wins: 0.

Every listed aggregate condition passes. This gate rejects the candidate because
seed 4 / seat 1 has a −50 TITAN own-cash tail.

## Usage

```bash
python paired_cell_tail_admission.py \
  --control /path/to/control.json \
  --candidate /path/to/candidate.json \
  --output /path/to/CELL-TAIL-ADMISSION.json \
  --markdown /path/to/CELL-TAIL-ADMISSION.md
```

The CLI exits 0 only for `ADMIT`; `INACTIVE` and `REJECT` exit 1. Evidence shape
errors terminate without writing an admission receipt.

## Focused validation

```bash
python -m py_compile paired_cell_tail_admission.py mechanism_witness.py \
  test_paired_cell_tail_admission.py
python -m unittest -v test_paired_cell_tail_admission.py
python mechanism_witness.py
git diff --exit-code -- MECHANISM-WITNESS.json
```

The package is standard-library only and changes no gameplay policy, archive,
configuration, release pointer, provider state, or Kaggle submission. Passing
it is a development evidence input for T08, never promotion authority by itself.
