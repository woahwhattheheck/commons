# Steerability Challenge public foundation

Source-bound, **pre-registration** competition tooling for the 2026 Steerability Challenge. This carrier intentionally does not register a team, create a Hugging Face organization/repository, download competition models, run GPU inference, upload a submission, contact organizers, or claim a leaderboard score.

The live competition page and guide observed on 2026-09-13 say the task is to reduce model dishonesty while minimizing regressions on general capabilities. The public composite description rewards improvement over the unsteered model and penalizes **regressions** in side effects; incidental capability gains are not rewarded. Final evaluation remains private and authoritative.

## Frozen public contract

This carrier binds its assumptions to competition-guide **v0.2 (2026-09-11)** and upstream toolkit main commit:

`f1d8b5fd6d9ed15d506f9445a93d55cb5c5b07df`

Current public dates:

- weekly evaluations begin **2026-09-24**;
- midpoint / model-organism release: **2026-10-19**;
- final upload deadline: **2026-11-21 AoE**;
- winners announced: **2026-12-01**;
- NeurIPS workshop: **2026-12-13**.

The three announced competition models are:

1. `google/gemma-4-31B-it`
2. `ibm-granite/granite-4.2-30b`
3. `Qwen/Qwen3.8-27B`

A submission contains one `.spipe` per model. The public guide says the three pipelines must have the **same structure** and may differ only in referenced trained artifacts. Tracks are nested: black-box → white-box → open. The official Starter Kit checker remains authoritative and is only distributed after team registration validation.

The organizers explicitly allow coding agents, while requiring participants to be able to explain prize-eligible solutions. They recommend access to roughly 80GB VRAM for the 27–31B reasoning models.

`contract.json` is a machine-readable snapshot, not a substitute for the live rules.

## What this foundation provides

### 1. Cross-model plan preflight

`submission_plan.py` makes model-specific structural drift difficult before a real `.spipe` exists. One shared recipe is declared once; per-model entries are allowed to contain only a `.spipe` path and trained-artifact bindings. Artifact placeholders such as `$artifact:honesty_vector` must be bound for all three models, with provenance, license, and SHA-256 metadata.

It also derives the **minimum plausible track** from declared access:

- `prompt`, `api_output` → black-box;
- `logits`, `activations` → white-box;
- `weights` → open.

That derivation is an internal preflight only. The toolkit / Starter Kit decides the official track.

```bash
python revenue/steerability_challenge/cli.py validate-plan plan.json
python revenue/steerability_challenge/cli.py validate-plan plan.json --require-files
```

`--require-files` additionally hashes declared artifacts and requires all three `.spipe` paths to exist.

### 2. Leakage-resistant local recipe scorecard

`scorecard.py` ranks **shared recipes**, not per-model tricks. Input is JSONL with normalized local measurements:

```json
{"recipe_id":"wb-gated-v1","model":"google/gemma-4-31B-it","seed":1,"metric":"honesty","kind":"target","baseline":0.42,"candidate":0.61}
{"recipe_id":"wb-gated-v1","model":"google/gemma-4-31B-it","seed":1,"metric":"knowledge","kind":"side_effect","baseline":0.79,"candidate":0.78}
```

Each recipe must contain identical model/seed/metric coverage across all three announced models. Positive oriented deltas mean improvement. The proxy:

1. averages target improvement;
2. charges only negative side-effect deltas as regressions;
3. computes every model/seed independently;
4. penalizes cross-model spread and run instability;
5. reports the worst-model composite;
6. marks the target-improvement / side-effect-regression Pareto frontier.

```bash
python revenue/steerability_challenge/cli.py rank local-evals.jsonl --output selection.json
```

This is **not** an attempt to reverse engineer the hidden evaluator. Its purpose is to keep local selection honest when the public leaderboard is downsampled and final evaluation includes held-out tasks.

### 3. Experiment matrix

```bash
python revenue/steerability_challenge/cli.py matrix --output experiment-matrix.json
```

The matrix converts public organizer guidance into staged hypotheses rather than pretending we already know a winning method:

- black-box honesty prompt floor;
- prompt + output-search composition;
- response-token activation steering with layer sweep;
- prompt + gated state-control composition;
- contrastive-scenario quality / sample-count ablation;
- open-track structural-adapter successor only after cheaper tracks justify it.

The guide specifically encourages multi-control composition, hidden-state use, layer sweeps, careful contrastive filtering, response-token or gated activation steering for Gemma-family large activations, and scenario diversity over raw contrastive sample quantity.

## Recommended execution sequence after registration

1. Obtain the organizer Starter Kit and freeze its exact hash/version.
2. Run the organizer submission checker unchanged; do not treat this carrier as a replacement.
3. Establish the cheapest black-box floor on the Starter Kit sanity data.
4. Preserve raw per-seed/per-model evidence. Do not select from a single convenient model.
5. Move into white-box response-token/layer-sweep experiments only when the local scorecard shows a defensible gain.
6. Fit model-specific artifacts while holding **pipeline structure fixed**.
7. Re-run the same recipe over all three models and multiple seeds.
8. Freeze `.spipe` bundles, provenance, environment/toolkit commit, artifacts and hashes.
9. Let the public weekly leaderboard inform hypotheses, not become a test set. Avoid iterative leaderboard overfit.
10. Before every upload, re-read the live guide and run the Starter Kit checker.

## Public/private boundary

This Commons carrier is deliberately public. It contains rules-grounding, validation, scorecard logic, and organizer-derived research hypotheses—**not** a tuned competition secret or trained artifact. A later private successor can hold the exact tuned pipeline/artifacts once registration and authorized compute exist.

Do not commit:

- Hugging Face tokens or credentials;
- registration identifiers;
- registration-gated Starter Kit files unless their redistribution terms allow it;
- private evaluation data or hidden labels;
- trained competitive artifacts intended to stay private;
- unverified leaderboard claims.

## Tests

From Commons root:

```bash
python -m unittest -v test_steerability_challenge.py
python -m py_compile \
  revenue/steerability_challenge/scorecard.py \
  revenue/steerability_challenge/submission_plan.py \
  revenue/steerability_challenge/experiment_matrix.py \
  revenue/steerability_challenge/cli.py \
  test_steerability_challenge.py
```

The tests lock: three-model/seed/metric completeness, regression-only side-effect charging, orientation of lower-is-better metrics, duplicate evidence rejection, instability penalties, recipe-structure hashing, model-specific-structure rejection, artifact binding/hash checks, track escalation, and deterministic experiment-matrix provenance.

## Sources

- Competition page: `https://steerability.github.io/competition/`
- Competition Guide v0.2 (2026-09-11): `https://steerability.github.io/competition/steerability-challenge-guide.pdf`
- Toolkit: `https://github.com/generative-computing/steerability`
- Toolkit `.spipe` concept docs: `docs/concepts/spipe.md` at the pinned commit above.
