# TITAN V5 animal cadence candidate

Status: **default OFF / evaluation only**. This package is additive to canonical V5 and does not change `main.py`, `titan_runtime.py`, `TITAN-CONFIG.json`, the release archive, or Kaggle submission bytes.

Promotion status: **BLOCKED until a source-pinned certificate builder supplies the exact current route identity and future-feed certificate used by evaluation.** The transform validates that evidence; it does not infer or fabricate it from route intent.

## Pinned engine theorem

The preserved engine is `reference/engine/kaggriculture.py` at source blob `3c202c7ee921da239356789e266b694635103fc4`.

The source-real behavior is:

- an animal survives one unfed end-of-day and escapes only when `consecutive_unfed >= 2`;
- scheduled base animal production is awarded even on that first unfed day;
- feeding gates consumption of a pending CARE bonus, so CARE value must not be discarded;
- every surviving animal sets `fertilizer_available = True` at every end-of-day, not every third day;
- duplicate same-tile FEED actions spend at most one WHEAT because the first successful FEED sets `fed_today`;
- `FERTILIZE` consumes one fertilizer and extends `fertilized_until_day`; it does **not** directly increment `yield_units`.

The last point is an explicit negative predecessor for the rejected “infinite fertilizer yield” hypothesis.

## Candidate

`alternate_feed.py::apply_alternate_feed(observation, selected, next_feed_certificate=..., route_identity=...)` is a pure selected-action transform. It replaces a selected `FEED` with `PASS` only when the animal tile is covered by a machine-checkable future-feed certificate, the actor actually carries WHEAT, the animal is on the exact zero-strike leg (`consecutive_unfed == 0`), no current or pending CARE value can be lost, and no same-tile selected CARE exists. Once the public state reports one unfed day, the next FEED is retained.

The certificate is bound to the exact public `observation_step`, route id, route-source Git blob, and current route-tail SHA256, and gives an exact future FEED step for each certified animal tile. The caller separately supplies the independently derived current `route_identity`; all three identity fields must match the certificate. Route switch, checkpoint/rejoin, reset, source drift, tail drift, or clock advance therefore requires a newly minted certificate. Empty, malformed, stale, or mismatched evidence fails closed and leaves the selected action untouched.

The transform preserves market rows, other unit actions, action-slot topology, and both inputs. Its report distinguishes actor actions suppressed from actual WHEAT avoided: multiple FEED actions on one animal tile may all be suppressed to skip that day, but count as only one saved WHEAT because that is the pinned engine's baseline spend.

## Focused checks

From `revenue/kaggriculture/cloud-execution-lab`:

```bash
python -B candidates/v5/animal-cadence/test_alternate_feed.py
python -O -B candidates/v5/animal-cadence/test_alternate_feed.py
```

The test module calls the preserved evaluator/engine for the survival boundary, base production, first-production CARE loss, duplicate-FEED spend, fertilizer refresh, and FERTILIZE-negative predecessors. Candidate tests separately cover route/source/tail/clock certificate custody, exact state types, CARE preservation, WHEAT spend, duplicate actor accounting, and action topology. They do not substitute an engine implementation.

## Evaluation handoff

The merged donor research artifact `candidates/v5/research/animal-feed-cadence/` already pins the official engine and current Arlene producer and emits a route census. The next evaluation step is to construct `route_identity` plus `next_feed_certificate` from the exact unchanged current-V5 route/tail, then apply this transform and compare against the same current-V5 baseline on identical opponent/seed/seat cells.

Record candidate identity, certificate-builder source identity, certificate provenance, engagement count (`report.changed`), actor FEED actions suppressed, unique-tile WHEAT saved, paired own-score and margin deltas, loss flips/new losses, and any CARE-bonus or escape divergence. Promotion stays blocked until that builder and matched current-line evidence exist; this package itself makes no activation claim.
