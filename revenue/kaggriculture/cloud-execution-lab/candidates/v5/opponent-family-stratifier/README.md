# F49 — Opponent-family stratifier

Operation: `TITAN-V5-F49-OPPONENT-FAMILY-STRATIFIER-ZSHF6R2-20260913`

This is the Wave-4 **F49** evidence/tooling lane. It consumes the already acquired top-30-union corpus (41 public submission versions, three completed public replay fixtures each) and discovers recurring opponent **behavior families** without reading leaderboard identity/rank/score into model geometry.

It does **not** change TITAN, mint a candidate, run Kaggle games, change `CURRENT`/defaults/releases, or submit anything. A classification is advisory. `UNKNOWN` is a required no-op/abstention state.

## Boundary

The feature vector accepts only the opponent's publicly recorded `action` stream. It derives:

- any/no-op rate;
- farmer/hands/market activity rates;
- early/mid/late channel activity and late-vs-early skew;
- action-signature diversity;
- a schema-independent 16-bucket semantic token sketch.

Numeric magnitudes are reduced to sign/presence buckets in the semantic sketch. Identity-like fields (`team_name`, `team_id`, `submission_id`, `episode_id`, `rank`, `score`, `seed`, etc.) are rejected recursively if injected into an action payload. Submission IDs appear in the report only as provenance membership labels **after** geometry is computed; changing those labels cannot change medoids/family IDs.

The input corpus itself remains truth-bounded: recorded actions are diagnostic, non-adaptive opponents, not reconstructed executable policies. This tool does not upgrade that evidence class.

## Method

For each of 41 versions:

1. authenticate each `.json.gz` replay against the source manifest SHA-256 and seed;
2. derive one behavior vector per replay;
3. use the first two replay vectors to form a median training signature;
4. build deterministic robust-scaled L1 k-medoids (`k=5` default);
5. classify the third replay as a held-out stability check;
6. abstain when the nearest-vs-second-nearest margin is below 10% or the discovered family has fewer than three target versions.

Family IDs are hashes of medoid feature vectors, not competitor identities. Phenotype names are descriptive only. Nominations deliberately route to existing Wave-4 mechanism owners rather than duplicating their code:

- `field-tempo` → F45 productive-harvest diagnostics;
- `cargo-logistics` → F43 deadline-cargo-return diagnostics;
- `market-active` → F46 saleable-quantity diagnostics;
- `late-liquidator` → F47/F44 terminal diagnostics;
- `sparse-reactive` or ambiguous → abstain / generic lower-tail guards only.

## Run on the real corpus

Use the archive referenced by `../gauntlet-top30-union/CORPUS-RECEIPT.json` (expected 41 targets / 123 fixtures). Point `--manifest` at that archive's `manifest.json`.

```bash
python -B f49_stratifier.py \
  --corpus /path/to/titan-v5-gauntlet-top30-union \
  --manifest /path/to/titan-v5-gauntlet-top30-union/manifest.json \
  --output F49-FAMILY-REPORT.json \
  --k 5 --min-support 3
```

A useful real-corpus receipt must report the source manifest digest, 41 targets, 123 replays, held-out coverage/accuracy, abstention count, family support, medoid digests, and per-family nominations. Do not call the discovered families adaptive opponent executables.

## Local hostile validation

```bash
python -B -m unittest -v test_f49_stratifier.py
python -O -B -m unittest -v test_f49_stratifier.py
python -m py_compile f49_stratifier.py test_f49_stratifier.py
```

The suite covers recursive identity leakage, numeric-magnitude invariance, terminal phenotype precedence, identity-label invariance of geometry, exact held-out stability, ambiguity abstention, replay digest/path/seed fencing, and the absence of leaderboard inputs from runtime feature keys.

## Promotion gate

F49 by itself cannot justify a policy change. A later owner may promote an opponent-conditioned policy only after all of these hold:

1. real-corpus report is reproducible from the pinned archive;
2. useful families meet minimum support and held-out stability;
3. conditioning uses only in-game publicly observable behavior and preserves `UNKNOWN → champion behavior`;
4. same-seed paired testing demonstrates lower-tail improvement without material regression in aggregate/strongest-opponent panels;
5. the owner explicitly releases the current V5 submission hold.
