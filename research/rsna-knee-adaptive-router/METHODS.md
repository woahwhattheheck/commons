# Frozen adaptive-compute experiment contract

The carrier is useful only if compute savings preserve enough discrimination to improve the competition objective. No synthetic result is a competition result.

## Arms

Evaluate on the same authorized folds and exact checkpoint family:

- **A / ALL** — strongest reproducible all-series baseline.
- **B / ROUTE-3** — first-stage label-covering route only.
- **C / ADAPTIVE** — ROUTE-3 plus at most the configured extra-series budget for studies with uncertain stage-1 labels.

Do not tune route thresholds, calibration, or model choice on public/private leaderboard outcomes. Freeze them from out-of-fold training evidence before final test inference.

## Evidence to retain

For every arm retain exact source/checkpoint/config digests; split identity; proof that calibration rows are OOF; per-target and macro AUC; studies/series/decoded-slice counts; full wall time and predictor time; upgrade rate; missing-preferred-plane frequency; failures/fallbacks; projected full-test wall time; measured/estimated peak VRAM plus available VRAM and safety multiplier; and the published efficiency-formula surrogate with its explicit reference parameters.

## Promote ADAPTIVE only if all pass

1. no report/test leakage and all calibration rows are OOF;
2. macro-AUC is >=99% of ALL **or** no more than 0.005 absolute below ALL;
3. projected wall time is >=30% lower than ALL;
4. at least 10/12 targets lose <=0.01 AUC and no target loses >0.025;
5. the efficiency surrogate improves across a predeclared plausible `maxAUC` band rather than one cherry-picked value;
6. runtime and VRAM budgets pass with safety margins;
7. exact submission validation produces every expected study once in canonical order.

If ROUTE-3 meets the AUC gates and is faster than ADAPTIVE, prefer ROUTE-3. If ADAPTIVE misses the AUC gates, kill it instead of hiding the regression behind runtime savings.

## Next authorized experiment

Plug the strongest current allowed public-pretrained image backbone into `run_dataset`, measure one bounded OOF panel, and return raw stage-1/stage-2 predictions plus timing/VRAM receipts. No leaderboard submission is needed to decide whether adaptive compute deserves promotion.
