# SOL-RATCHET — TITAN V3 L01 leaderboard-objective gate

Operation: `titan-v3-l01-own-score-gate-20260909-sol-ratchet-01`

## Defect

The current L01 LAND paired-panel gate promoted any changed candidate with zero new head-to-head losses and positive mean margin. It did not require positive candidate terminal reward.

The retained source-pinned historical evidence therefore reported `ADVANCE` even though the eight changed cells lost 68,040 candidate-score points in total (`-8,505` per changed cell; `-354.375` across the complete 192-cell grid). Margin improved only because rival score fell further.

## Repair

The gate now names `scores[candidate_seat]` as the primary leaderboard metric and admits a candidate only when all of these are true:

- at least one paired cell changed;
- no new head-to-head loss was introduced;
- mean candidate terminal-score delta is positive;
- candidate terminal-score delta is nonnegative in every observed opponent stratum;
- candidate terminal-score delta is nonnegative in both candidate-seat strata; and
- mean margin delta is positive as secondary evidence.

Negative candidate score overall or in any opponent/seat stratum is `REJECT`; zero candidate score or a non-positive secondary margin is `HOLD`; no changed cell is `NULL`. Reports expose the decision reason, primary/secondary metric, exact candidate/rival score sums, per-opponent and per-seat candidate-score deltas, and every failing stratum.

## Exact retained replay

Input artifact: `titan-v3-land-admission-current-34402506924-1`

Artifact ZIP SHA-256: `4c4c28a8203540d161397f04cfb8fbd58489a14b067b508d42a15fb0b2650c65`

Input game hashes remain:

- canonical: `599c2649999fa291d90b04ba8b07f06849da19fef2f73fb1caaa4ca6a885fb61`
- LAND: `762c7b2525ca2c75adef62d839e341f193faa4359a0fddf4d700bdb5d14d7ead`

All pre-existing paired rows, records, changed-cell identities, normalization sites, margin metrics, and own/rival means reproduce exactly. The repaired decision is:

```json
{
  "verdict": "reject",
  "verdict_reason": "candidate terminal score regresses overall",
  "mean_own_delta": -354.375,
  "sum_own_delta": -68040.0,
  "mean_margin_delta": 674.875,
  "negative_own_score_opponents": ["arlene"],
  "negative_own_score_seats": ["0"]
}
```

## Predecessor-discriminating coverage

The suite includes a Simpson-style seat-collapse witness: aggregate candidate score is positive, every opponent stratum is positive, margin is positive, and no new loss appears, yet candidate seat 1 regresses. The repaired gate rejects it and reports the exact failing seat.

## Validation

- `python -B -m unittest -v test_panel_delta.py`: 11/11 PASS
- `python -m py_compile panel_delta.py test_panel_delta.py`: PASS
- exact 192-game retained CLI replay with `--expect-historical-l01`: PASS
- common pre-existing evidence-field equality against the retained `DELTA.json`: PASS
- exact tested blobs: `panel_delta.py=ec69862a6a32456ba750a43243c09f650bacbba4`, `test_panel_delta.py=20a5a59b2794c70ab9d2fa91b165c8ce11a2dc86`

## Scope

Three paths only: `panel_delta.py`, `test_panel_delta.py`, and this receipt. No candidate policy, route, gameplay mechanism, evaluator, official engine, seeds, opponent, runtime, archive, config, default entrypoint, provider, or Kaggle submission mutation.
