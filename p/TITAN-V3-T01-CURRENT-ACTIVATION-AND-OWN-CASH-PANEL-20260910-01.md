# TITAN-V3-T01-CURRENT-ACTIVATION-AND-OWN-CASH-PANEL-20260910-01

## Claim

- Slack claim: `#titan-kaggriculture` timestamp `1789067000.047679`
- Current base: `2e2e7e52fd2d5c62117ac49c7f1eabb505078ffb`
- Current canonical archive: `5f6a4153e502713b9467776eafe7464af650584149173ce7507a31a1b2af60f1`
- Current source manifest: `3249398b6aa56d1b3464db8d0cce5aa35e8edee397fc4341bd710d1f74dad469`
- Superseded stale-base heads: `75e0e265db0432d054d509932fb431ede8f03565`, `4e11eb695a0c49a7cfb67c2ebad4c00214cc03b8`, `b2bbffd285eb7c88d0682602c93e29d16f460c01`
- Owner: SOL-SETTLE
- Source under test: `candidates/v3-terminal-settlement/terminal_settlement.py`
- Existing source disposition before this operation: `SOURCE_CANDIDATE_TESTED_GAME_UNMEASURED`

## Exact work

This operation creates one additive exact-current carrier and one evidence lane.
The carrier intercepts only exact-current controller construction and installs an
instance-local wrapper around the current `FinalPressureAgent` return seam. The
original `_early_capital_selected` completes first; then T01 sees its returned
action before `_finish_production` commits. Cold load, projection, and settlement
therefore execute inside canonical `main.agent` and its one-second outer timer.
Canonical fallback and reconstruction retain sole authority.

The runner executes an 8-seed × 2-opponent × 2-seat paired panel against Arlene
and submitted V1: 32 matched cells per variant, 64 official games total.

The locally patched evaluator snapshots only the step-718 pre-resolution
observation/configuration and simultaneous actions. The auditor recomputes the
certificate from the baseline action with exact current `scheduler.post_units`,
requires the candidate action to match it, and checks every activated cell's
observed own terminal cash against the reported literal lower bound.

## Admission gate

All of the following are required for `ADVANCE`:

- exact 32-cell matched grid and pinned official 720-state/719-action lifecycle;
- identical preterminal observation/configuration and opponent terminal action;
- at least one action-bound certified activation;
- observed own delta at least the certified minimum in every activated cell;
- positive global mean and median own terminal cash;
- positive global mean margin;
- no negative own-cash cell or margin cell;
- no negative opponent×seat own-cash or margin mean;
- zero W→T, W→L, or T→L outcome regressions.

Zero activation or any failed score gate is retained as `REJECT`. A structurally
invalid or incomplete panel fails separately. The exact-parent workflow runs
current canonical package/import validation before the game step; a red base burns
zero panel games.

## Authority boundary

`ADVANCE` authorizes only a separate one-tree composition experiment. This
operation does not edit canonical runtime/config/archive/pointer bytes, rebase or
publish the V3 one-tree branch, merge itself, submit to Kaggle, mutate provider
state, or make a leaderboard claim. Negative results remain durable evidence.
