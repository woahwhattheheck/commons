# TITAN V5 animal-cadence matched evaluation

Status: **evaluation harness only; promotion remains blocked until `RESULTS.json` and `RECEIPT.json` are produced by a complete matched run.** This subtree does not modify canonical runtime, defaults, release archives, current pointers, or provider/Kaggle state.

The runner binds the current canonical archive (`sha256=74c6a2e59e720609b1d216317bb9651399e05fdd045ac2129e15c000ff0f3894`, 466,769 bytes), official engine blob `3c202c7ee921da239356789e266b694635103fc4`, Commons evaluator blob `1fb6b655bb4ca1e1684be165a8ef513e2e6c2325`, existing V5 matched-game helper blob `aefdc6cff09cc7693a5ae0da01e88756171a65f0`, animal-cadence transform blob `e5f545c452e54337e978c3fa553535e967d50569`, certificate builder blob `e7b7e7d0372e163c1b83e481d823a82a9fbedeab`, and current archive-pointer blob `2797bf01b58803b0d0f99abfa776c78c91961fcb`.

`candidate_entry.py` first obtains the untouched current-V5 action. Only when that runtime call reports `status=completed` does it ask the source-pinned authority for a certificate and call the published pure transform. Every deadline fallback, malformed state, source/profile mismatch, authority decline, or bounded adapter exception returns the original action unchanged. Engagement counters are evidence output only.

`paired.py` reuses the repository's official interpreter, process-isolated evaluator, pack adapter, and reference-policy bank. For every `(opponent, seed, seat)` cell it runs the same current archive twice, baseline and candidate, with `apex_v7` and `arlene_v14` as the default opponent set. It records source/archive/engine/opponent identities, authority and candidate engagements, every decline/error bucket, FEED suppressions, unique-tile WHEAT saved, paired own-score and margin deltas, W/T/L and loss flips/new losses, engine-observed animal escapes, and CARE-bonus state divergence. It refuses to publish final result/receipt bytes on duplicate/unmatched/incomplete cells, non-finite metrics, or zero candidate engagement.

Focused contract checks:

```bash
python -B candidates/v5/animal-cadence/evaluation/test_paired.py
python -O -B candidates/v5/animal-cadence/evaluation/test_paired.py
python -m py_compile candidates/v5/animal-cadence/evaluation/{paired.py,candidate_entry.py,test_paired.py}
```

A mounted Linux checkout with the existing engine source pack can execute the bounded claimed panel from `revenue/kaggriculture/cloud-execution-lab` (replace `/path/to/engine` with the existing pinned official-engine directory):

```bash
python -B candidates/v5/animal-cadence/evaluation/paired.py \
  --kg-root .. \
  --engine-dir /path/to/engine \
  --output /tmp/titan-v5-animal-cadence-eval \
  --seeds 1209121623,1209121625 \
  --seats 0,1 \
  --opponents apex_v7,arlene_v14
```

That is 8 matched cells / 16 full games. If the complete run has zero candidate engagement, the finalizer fails closed; only then should a larger predeclared seed set be scheduled without changing policy or opponent identities. A negative economic result is valid evidence and must not be rewritten into a promotion claim.
