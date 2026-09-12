# ASTRA-SPECTRUM — gauntlet panel identity and multiplicity control

This is an additive analysis seam inside the single TITAN V4 tree. It does not add an opponent, run a game, alter the candidate, change defaults, or make a promotion decision.

## Why

A headline such as “31 opponents / 186 games” can overstate strategic diversity when multiple displayed labels belong to the same strategy family or are exact aliases of the same source bytes. Repeating one archetype five times gives it five votes in a raw per-label average even if those rows are only parameter siblings—or literally identical source. Score equality is **not** evidence of semantic identity, so this tool never collapses rows based on outcomes.

`gauntlet_panel_identity.py` requires publishers to declare, for every displayed opponent label:

- `id`: the displayed identity;
- `kind`: `recorded_trace`, `archetype`, `live_agent`, or `mirror`;
- `family_id`: explicit strategy-family ownership;
- `variant_id`: unique within that family;
- `source_sha256`: exact source/policy/trace identity used for that row.

Outcome-bearing rows may also provide exact integer `wins`, `losses`, `draws`, and `total_margin`. The panel must be all identity-only or all outcome-bearing; mixed evidence fails closed.

## Fail-closed identity rules

- duplicate JSON keys are rejected before interpretation;
- duplicate opponent IDs and duplicate `(family_id, variant_id)` pairs are rejected;
- source digests are lowercase SHA-256 only;
- the same exact source digest may be repeated only inside the same family and kind; re-labeling identical bytes into multiple families is rejected;
- mirror and non-mirror rows may not share a family;
- Python bools are not accepted as integer counts;
- no family is inferred from names and no semantic equivalence is inferred from equal scores.

Exact-source repeats inside one family remain visible as `alias_groups` and contribute `alias_excess`, but they get one source vote in balanced views.

## Three views

When outcomes are supplied, the report emits all three instead of silently choosing one:

1. `raw_game_weighted_counts` and `raw_label_mean` — what the displayed table literally contains;
2. `source_balanced_mean` — identical source aliases share one vote;
3. `family_balanced_mean` — aliases first collapse by source inside a family, then every explicit strategy family receives one vote.

This is a multiplicity diagnostic, not a statistical independence proof. Distinct hashes can still implement highly correlated policies. Conversely, two variants in one family remain distinct source identities even if they happen to produce the same score.

## Run

```bash
cd revenue/kaggriculture/cloud-execution-lab/candidates/v4/research/replay-loss-autopsy
python -m unittest -v test_gauntlet_panel_identity
python -O -m unittest -v test_gauntlet_panel_identity
python gauntlet_panel_identity.py PANEL-IDENTITY.json --output PANEL-IDENTITY-AUDIT.json
```

Input schema: `titan.gauntlet.panel_identity.v1`. Output schema: `titan.gauntlet.panel_identity.audit.v1`.

The pure API is `gauntlet_panel_identity.audit(document)`. It is intended to sit in front of the current gauntlet table/consumer stack: REFORGE, BASALT, ORCHARD, QUIETBOX and future gauntlet readers can consume the same identity receipt instead of each inventing family weighting.

`promotion_decision` is always `NOT_ASSESSED`.
