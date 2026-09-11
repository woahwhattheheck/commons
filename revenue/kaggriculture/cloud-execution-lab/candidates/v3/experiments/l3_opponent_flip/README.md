# L3 opponent-flip evidence — 2026-09-11

This directory is **execution evidence only**. It does not change `overlay/**`, V3.1 defaults, package inputs, evaluator bytes, opponents, or submission behavior.

## Question

Does the L3 factor (“do not run E184 `reserve_sales()` at absolute steps >=648”) have a stable competitive sign across opponents, or is the strong positive result opponent-conditioned?

## Exact source custody

The run materialized the ready V3.1 Slack package `F0C18AXAL04`, whose README binds the package to Git commit `d5eca5b1230258ec583f8026f6a3b422ed15cde0` and inner archive SHA256 `e4e5a3acfe4984c89c22c7aa841b4ddd6efe4f4cd71e507d1dabecbb6e865849`.

Executed source SHA256 values are recorded in `L3-OPPONENT-FLIP-20260911.json`. The committed `l3_factor_telemetry_wrapper.py` is the exact wrapper used for the low-seed opponent-flip runs (SHA256 `d420aef48adf5e7e29f07cc2bfc9c91ae6dc4ee14e327e192a111e1f02061ead`). It assumes the ready package is extracted at `/tmp/v31base`, matching the execution VM.

The wrapper is deliberately **factor-equivalent, not exact PR #12369/#12372 bytes**. It imports the exact packaged R04 and replaces only the `reserve_sales()` callable so that steps `<648` call the original unchanged and steps `>=648` return without mutating the real action/state. For causal telemetry, the skipped original is executed only on `deepcopy()` snapshots; those counterfactual mutations are never applied to the candidate.

## Reproduction shape

The official packaged evaluator was invoked with explicit packaged loader and engine paths. Representative commands:

```bash
# Exact V3.1 control vs vendored Arlene (paired-control arm)
python /tmp/v31base/checks/reference/evaluator/evaluate.py \
  --loader /tmp/v31base/checks/reference/evaluator/loader.py \
  --engine-dir /tmp/v31base/checks/reference/engine \
  --candidate /tmp/v31base/main.py \
  --opponent arlene=/tmp/v31base/reference/next-panel/vendor/arlene.py \
  --seeds 101

# L3 factor vs the same Arlene
L3_TELEMETRY=/tmp/l3_telemetry.jsonl \
python /tmp/v31base/checks/reference/evaluator/evaluate.py \
  --loader /tmp/v31base/checks/reference/evaluator/loader.py \
  --engine-dir /tmp/v31base/checks/reference/engine \
  --candidate ./l3_factor_telemetry_wrapper.py \
  --opponent arlene=/tmp/v31base/reference/next-panel/vendor/arlene.py \
  --seeds 101

# Direct competitive head-to-head: L3 factor vs exact V3.1
L3_TELEMETRY=/tmp/l3_telemetry.jsonl \
python /tmp/v31base/checks/reference/evaluator/evaluate.py \
  --loader /tmp/v31base/checks/reference/evaluator/loader.py \
  --engine-dir /tmp/v31base/checks/reference/engine \
  --candidate ./l3_factor_telemetry_wrapper.py \
  --opponent v31=/tmp/v31base/main.py \
  --seeds 101
```

The evaluator emits both candidate seats for each seed. Arlene values in the receipt are paired `ΔM = Δown - Δrival` versus an exact-V3.1 control run under the same seed/seat/opponent. Exact-V3.1 values are direct candidate head-to-head margins (`candidate_score - opponent_score`). An exact-V3.1-vs-itself control on seed 101 was 94543/94543 in both candidate-seat runs (0 margin).

## Results

### Wrapper validation on the frozen Arlene panel

Frozen seeds `2611151001..2611151008`, both seats: **16/16 positive, mean +204.75 ΔM, range +110..+339**. This exactly reproduces the already-published L3 factor result and is a sanity check that the wrapper exercises the intended mechanism.

### Same low seeds, opponent flip

Seeds `101..108`, both seats:

- vs vendored Arlene, paired to exact V3.1 control: **16/16 positive, mean +233.0625 ΔM, median +216, range +123..+342**.
- direct vs exact V3.1: **16/16 negative, mean -335.625 head-to-head margin, median -325, range -485..-149**.

The sign therefore flips cleanly with the opponent on the same seed set. Counterfactual telemetry also shows genuinely avoided reservations in sampled low-seed runs (for example seed 102: 60 causally active skipped reservations / 480 avoided SELL+debt units), so the negative direct matches are not caused by an inert gate.

## Decision boundary

This packet is **not** evidence that L3 is universally bad. It is evidence that positive Arlene / selected-opponent panels do not justify a distribution-wide default-ON conclusion by themselves. Any promotion gate should include an opponent mixture representative of the expected leaderboard and should report true causal avoided reservation quantities, not only `suppressed_steps` callback opportunities.

The safe disposition remains: preserve the clean L3 carrier, keep the default flip on HOLD until the wider opponent/seed distribution is understood, and evaluate exact candidate package bytes before release.
