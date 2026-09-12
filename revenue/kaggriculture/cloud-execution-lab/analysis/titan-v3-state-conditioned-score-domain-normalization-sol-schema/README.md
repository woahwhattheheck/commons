# SOL-SCHEMA — state-conditioned SELL score-domain normalization

Operation: `TITAN-V3-STATE-CONDITIONED-SCORE-DOMAIN-NORMALIZATION-20260910-01`

This is a **zero-game-seed donor repair** for PR #12058 at exact head
`8d1e00f6dd377485d966109217e824937eef1c80`. It does not amend that spent
head, rerun its bank, mutate the canonical runtime, or claim promotion.

## Retrieve the exact donor

`DONOR.tar.gz.b64` is a review artifact rather than an activated runtime. Decode
it from this directory with:

```bash
base64 -d DONOR.tar.gz.b64 > titan-score-domain-normalization-donor.tar.gz
printf '%s  %s\n' \
  '7a396e67a1ec685f7a83252702ac72b8868d9fec37b3706172e315300d09ada1' \
  'titan-score-domain-normalization-donor.tar.gz' | sha256sum -c -
mkdir donor && tar -xzf titan-score-domain-normalization-donor.tar.gz -C donor
cd donor && ./run_contracts.sh
```

The archive contains the full replacement overlay, 12 adversarial unit
contracts, deterministic rank-inversion witness generator, exact-source binding
receipt, and bound regression evidence. The readable witness and evidence are
also retained beside this README for immediate review.

## Why the original selector is unsafe

The selected SELL optimizer returns a report whose score-bearing fields are in
one semantic domain:

```text
true relative value = TITAN own value - rival receipts
```

PR #12058 executes a second optimizer pass with tuple element zero replaced by
TITAN own value. If that second result object escapes unchanged, its
`acceptance_score`, `worst_relative_gain`, `weighted_expected_gain`, and each
scenario's `relative_value` are λ=0 own-value numbers. The live caller then
compares those numbers against ordinary λ=1 true-relative reports in
`seller_choice_rank`, and sums them in `joint_plan_metrics`.

That is a type error expressed as valid floats. The machine-readable
`RANK-INVERSION-WITNESS.json` gives a two-product predecessor: product A's raw
λ=0 own-gain score is 20 and incorrectly outranks product B's true-relative
score 10, although A's true-relative score is only 1.5. Normalization restores
B as the deterministic winner.

## Repair theorem

An own-value candidate may escape only when every canonical scenario proves:

1. candidate own value is strictly above both the authored reference and the
   incumbent-selected plan;
2. candidate true-relative value is strictly above the authored reference;
3. candidate true-relative value is not below the incumbent-selected plan; and
4. the modeled W/T/L outcome does not regress.

The third rule is the critical correction to the original #12058 gate. It
turns the state-conditioned mechanism into a Pareto-safe tie-breaker rather
than allowing own-cash gains to purchase modeled margin or outcome losses.

## Outward-schema normalization

The repair never exports the λ=0 result dictionary. It starts from a deep copy
of the exact first λ=1 incumbent report, validates the complete 20-field live
schema and all non-score metadata, then rebuilds these fields from the original
unmodified scorer for the admitted candidate plan:

- `scenarios[*].reference_relative_value`
- `scenarios[*].relative_value`
- `scenarios[*].own_receipts`
- `scenarios[*].rival_receipts`
- `scenarios[*].carry_units`
- `worst_relative_gain`
- `acceptance_score`
- `scenario_weights`
- `weighted_expected_gain`

Any schema, plan, reference, metadata, weight, score identity, or finiteness
drift returns the **exact first incumbent object by identity**. No partially
normalized object is returned.

## Evidence already spent

The original #12058 development panel completed 32 paired cells before its
terminal admission stage failed on a ledger mismatch. Its retained artifact
reported:

- mean own cash: `-27.875`
- total own cash: `-892`
- median own cash: `-9`
- mean margin: `-40.375`
- support: `4 positive / 16 negative / 12 zero`
- action-trace changes: `24/32`

Those seeds are terminally spent. `REGRESSION-EVIDENCE.json` binds the exact
run, artifact, archive, runtime tree, and selected-core blob. This donor uses
that result only as developmental motivation. It spends zero new game seeds
and does **not** claim the repair improves terminal economics.

## Verification performed

The 12 adversarial contracts pass and cover true-relative regression versus the
incumbent, exact incumbent-object fallback, full optimizer-info schema drift,
reference/plan metadata drift, scenario-weight drift, candidate exceptions,
non-strict rules, non-finite and boolean score values, source binding,
idempotence, λ=0/λ=1 per-product rank inversion, and λ=0/λ=1 joint-plan
aggregation corruption.

`REAL-SOURCE-BINDING.json` records a successful installation against the exact
`selected_sell_core.py` extracted from workflow artifact `10171987290` (Git
blob `f23d3a8b5ee5e82029026e7f8f44eb36c143a5a3`).

## Integration boundary

The owner of PR #12058 retains mechanism, panel, integration, and release
custody. A successor should transplant this donor into a new head, use a new
immutable label and fresh seed bank only after exact review, and apply the
stronger causal/tail evidence contracts already owned by the promotion-closure
lane. No Kaggle upload or provider action is authorized here.
