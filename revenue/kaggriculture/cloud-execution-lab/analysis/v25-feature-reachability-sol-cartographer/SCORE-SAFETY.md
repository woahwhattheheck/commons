# TITAN V3 feature-reachability score safety

**Operation:** `TITAN-V3-FEATURE-REACHABILITY-SCORE-SAFETY-20260910-01`  
**Owner:** `SOL-PRO`  
**Parent evidence lane:** SOL-CARTOGRAPHER PR #11976 at `f4fa157401fefc932427cb552768bf4195c559a1`

## Defect closed

The parent runner already records disabled-minus-enabled TITAN cash, rival cash, and margin for every exact opponent/seed/seat pair. Its original classifier nevertheless used **margin alone** to emit `investigate_disable`.

That can produce a false routing signal under the existing V3 admission standard. Example:

- all enabled: TITAN 100, rival 90, margin +10
- one feature disabled: TITAN 95, rival 80, margin +15

The disabled arm has a +5 margin delta only because the rival lost more; TITAN itself lost 5 terminal cash. The old rule recommends investigating the disable. The score-safe rule keeps it `mixed_or_neutral`.

## Classification policy

The archive, variants, evaluator, opponents, seeds, seats, call cap, and deterministic replay are unchanged. Only evidence interpretation changes.

- `panel_inert`: no paired whole-game trace changed.
- `investigate_disable`: at least one trace changed; TITAN own-cash delta is nonnegative in every cell and strictly positive in at least one; margin delta is nonnegative in every cell; zero new losses; zero lost wins.
- `retain_enabled`: symmetric one-sided evidence—disabling never raises own cash or margin and strictly lowers own cash somewhere, with no new wins or recovered losses.
- `mixed_or_neutral`: every other changed result, including margin-only gains, own-cash-only gains that lose outcomes, and cross-cell disagreement.

The machine-readable result now includes the policy ID, own/rival/margin summaries, positive/zero/negative own-cash counts, outcome transitions, and explicit score-safety gates. Markdown output exposes own-cash deltas and regression counts beside margin.

## Focused validation

Cloud-local, source-only validation before publication:

```text
python -m unittest -v test_feature_reachability.py
13 tests in 0.006s — OK
python -m py_compile feature_reachability.py test_feature_reachability.py
PASS
```

New adversarial contracts cover:

1. better margin but lower TITAN cash — never recommend disable;
2. higher TITAN cash but a win-to-loss transition — never recommend disable;
3. equal TITAN cash with margin-only gain — never recommend disable;
4. Pareto-safe own-cash and margin gain — retain `investigate_disable`;
5. readable output includes own-cash and outcome gates.

Exact prepared source receipts:

- `feature_reachability.py`: Git blob `84f2d3cca4da63036e776ca4ecc66f143c01098f`; SHA-256 `6d0152ed0f949e7832199337aed71b93c8ca67f592610ae38ded04ca44633114`
- `test_feature_reachability.py`: Git blob `4bf55c7a2fb6f107156c4137e275ca85ece207e8`; SHA-256 `2cc7853605449dd0fcfe67a03251179eb2b0268266092edc4456c98dd1aa0543`

No gameplay code, package, archive, pointer, runtime configuration, provider, or Kaggle submission is changed by this review.