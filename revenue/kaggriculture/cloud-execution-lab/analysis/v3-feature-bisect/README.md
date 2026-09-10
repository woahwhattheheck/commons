# TITAN V3 config causal bisector

This lane answers a narrow question with official-engine evidence:

> Which newly enabled V2.5 mechanism, or interaction between two mechanisms, is
> causing the current policy to lose outcomes or relative margin on the same
> opponent/seed/seat cells?

The current release manifest explicitly says that the changed V2.5 archive has
no full-game evidence for its changed bytes. A leaderboard movement cannot tell
us which component caused the movement, and aggregate candidate totals cannot
separate a candidate effect from a changed cell mix. This tool therefore builds
**config-only counterfactuals from the exact current archive** and compares them
on an exact paired grid.

It does not edit `TITAN-CONFIG.json`, the current archive, runtime source, a
Kaggle submission, or any provider resource. Its strongest output is a nominee
for a larger preregistered panel.

## Contracts

`feature_bisect.py` has three fail-closed stages.

1. **prepare**
   - binds every source archive by SHA-256;
   - rejects absolute paths, traversal, duplicate members, links, devices, and
     oversized members;
   - materializes a baseline, one-key removals, bounded two-key removals, and
     optional immutable historical controls;
   - proves that a config ablation changes exactly `TITAN-CONFIG.json` and that
     every other archive member is byte-identical;
   - seals a member-by-member manifest for each candidate and the complete
     matrix.
2. **run**
   - verifies every candidate tree before execution;
   - invokes the existing process-isolated official evaluator without changing
     it;
   - schedules the same explicit opponent, seed, and both-seat grid for every
     candidate;
   - requires the evaluator's independent first-cell trace/score replay;
   - verifies that evaluation did not add, delete, or mutate candidate bytes;
   - writes hash-bound stdout, stderr, report, command, and resume receipts.
3. **analyze**
   - rejects failed, missing, duplicate, or unexpected cells;
   - rejects engine, evaluator, loader, opponent, seed, RNG, or limit drift;
   - rejects a report whose entrypoint hash does not match its candidate
     manifest;
   - reports paired W/T/L flips, own-score delta, reacting-rival delta, relative
     margin delta, worst cell, quartiles, trace divergence, and pair
     interaction;
   - nominates a config removal only when it has no W→non-W reverse flip, does
     not reduce wins or increase losses, has positive mean paired margin, and
     improves more cells than it harms.

A nomination is labelled `ESCALATE_FULL_PANEL`, never `PROMOTE`.

## Reproduce the focused contracts

From this directory:

```bash
python -m py_compile feature_bisect.py test_feature_bisect.py
python -m unittest -v test_feature_bisect.py
```

The suite includes archive traversal/link/duplicate rejection, wrong archive
identity, unknown/disabled toggles, exact non-config preservation, historical
control isolation, candidate tampering, sealed-artifact tampering, candidate
report swaps, engine drift, failed cells, duplicate cells, missing cells, an
unpaired/Simpson-style partial-grid trap, pair-interaction arithmetic, and a
fake evaluator exercising the complete run/resume/analyze path.

## Prepare an exact current matrix

```bash
LAB=revenue/kaggriculture/cloud-execution-lab
TOOL=$LAB/analysis/v3-feature-bisect/feature_bisect.py
ARCHIVE_SHA=$(python - <<'PY'
import json
print(json.load(open('revenue/kaggriculture/cloud-execution-lab/runtime/integrated-selected/CURRENT-ARCHIVE.json'))['sha256'])
PY
)

python "$TOOL" prepare \
  --baseline "current-v25=$LAB/exports/titan-current.tar.gz@$ARCHIVE_SHA" \
  --control "submitted-v2=$LAB/exports/historical/titan-e363125093463d1f7a63a01aecb70646344dae5b318952e13a1b1641e2043e58.tar.gz@e363125093463d1f7a63a01aecb70646344dae5b318952e13a1b1641e2043e58" \
  --toggle early_capital \
  --toggle operating_stock \
  --toggle idle_fertilizer \
  --toggle crop_release \
  --pair early_capital,crop_release \
  --pair operating_stock,crop_release \
  --pair idle_fertilizer,crop_release \
  --output-dir .titan-v3-bisect/matrix
```

The historical control is optional. If it is supplied, its filename and bytes
must match the declared digest.

## Run identical official-engine cells

```bash
python "$TOOL" run \
  --matrix .titan-v3-bisect/matrix/matrix.json \
  --evaluator "$LAB/reference/evaluator/evaluate.py" \
  --engine-dir "$LAB/reference/engine" \
  --opponent "arlene=$LAB/reference/next-panel/vendor/arlene.py::agent" \
  --seeds 261140014,261140015 \
  --results-dir .titan-v3-bisect/results
```

Interrupted exact cells are resumable only when the complete run contract,
candidate manifest, and report hashes match. A failed or stale receipt is not
silently reused.

## Analyze

```bash
python "$TOOL" analyze \
  --runs .titan-v3-bisect/results/runs.json \
  --output .titan-v3-bisect/analysis.json \
  --markdown .titan-v3-bisect/analysis.md
```

The JSON retains every paired cell delta. The Markdown is a compact ranking for
builders. Controls are ranked for context but cannot be described as a
config-only causal effect.

## Interpretation boundary

A small fixed-cell screen is useful for regression localization, not rating
estimation. A positive removal can mean the removed mechanism is harmful, that
it interacts badly with another enabled mechanism, or that the screen is too
narrow. The next action is a larger source-pinned both-seat panel against
multiple reacting opponents. Canonical bytes remain unchanged until that panel
passes and the existing integration owner accepts the result.
