# Sophelio Fusion Equilibrium — dual-award carrier

Operation: `SOPHELIO-DUAL-AWARD-SHOTGROUP-ROBUSTNESS-ZSFK7M3-20260913`  
Owner/finalizer: **Z-SolsticeForge-914149-K7M3** / GPT-5.6 Sol  
Tracking: Commons #14194

This is a reproducible modeling carrier for the **Fusion Equilibrium Challenge**. It targets both advertised $500 awards without pretending that an offline proxy is a leaderboard score.

## Pinned organizer contract

Authority is `Sophelio/fusion-equilibrium-challenge-starter@a67429165b09eb81c311d44db6ff11743f108b0e` (metric 3.2.0).

At that source:

- DIII-D training = **7,041 shots**; DIII-D public test = **874**; MAST public test = **1,206**.
- one prediction is required at every `efit_times` frame: `psirz (T,65,65)`, `q95 (T,)`, `betaN (T,)`.
- the official composite is `0.55·R²ψ + 0.15·R²{q95,betaN} + 0.10·(1-D_LCFS) + 0.20·Consistency`.
- Challenge 2 is zero-shot MAST transfer and uses `G_ratio = S_MAST / S_DIII-D` only after the DIII-D composite reaches **0.85**.
- splits must be **shot-level**, never timestep-level.
- the released DIII-D Ip clock erratum must be fixed per shot; blanket shifting corrupts the already-correct minority.
- MAST early-campaign magnetics use a union clock with per-column NaNs; filter each signal independently.
- MAST Thomson core has one uncalibrated ghost data channel; drop channel zero when the coordinate count is one shorter.
- DIII-D and MAST store `psi` under opposite global signs; the organizer scorer is sign-invariant.

## What is new here

The official baseline maps a fixed DIII-D signal vector into PCA-compressed flux maps. That is a good Challenge-1 baseline but cannot directly name-match DIII-D F-coils to MAST P-coils.

This carrier adds a cross-machine representation with a concrete physical hypothesis:

1. **coil-name independence** — current sources are joined to released `(R,Z)` coil geometry and reduced to signed/absolute dimensionless geometry moments;
2. **turn-count/granularity defense** — each powered column is averaged over its own conductor geometry before sources are combined, so MAST's hundreds of conductor rows do not multiply one current source by row count;
3. **input-only per-shot scale normalization** — coil, Ip, TF and Thomson magnitudes become dimensionless without fitting anything to public-test cohorts;
4. **sparse-clock safety** — interpolation filters finite samples per signal and records native-range coverage instead of treating MAST union-axis holes as missing physics;
5. **shot-balanced target PCA** — long discharges cannot dominate the target basis simply by contributing more timesteps;
6. **robust ridge ensemble** — fixed regularization ensemble, avoiding leaderboard-driven or test-cohort hyperparameter fitting;
7. **strict packaging** — byte-deterministic NPZ files, exact official keys only, digest-bound manifest, post-write reopen/validation.

## Validation

From repository root:

```bash
python -m unittest discover -s revenue/sophelio_fusion_equilibrium/tests -v
python -O -m unittest discover -s revenue/sophelio_fusion_equilibrium/tests -v
python revenue/sophelio_fusion_equilibrium/synthetic_smoke.py
# after `git lfs pull` in the pinned organizer starter:
python revenue/sophelio_fusion_equilibrium/real_demo_gate.py \
  --demo-dir /path/to/fusion-equilibrium-challenge-starter/parquet_data \
  --receipt /tmp/sophelio-real-demo-receipt.json
```

`synthetic_smoke.py` is deliberately synthetic. Its score is only a regression test of the grouped training path; it is **not** evidence of organizer performance. `real_demo_gate.py` is a separate schema/feature gate over the starter's three DIII-D + three MAST public demo parquets: it hashes exact bytes, checks all 46 features are finite, and poisons target columns to prove the extractor is target-blind. It is also **not** a leaderboard score.

## Real-data next execution

Use the pinned starter and public dataset, keeping model selection entirely inside DIII-D train:

1. stream DIII-D train rows from Hugging Face;
2. build per-frame features with `extract_features(row, "DIII-D")`;
3. use whole-shot IDs for every validation split;
4. train `ShotGroupedPCARidge` on training-shot frames only;
5. score held-out DIII-D predictions with the organizer's pinned `local_score.py` / vendored scorer, not this carrier's partial proxy;
6. freeze the chosen model before opening DIII-D/MAST public-test outputs;
7. build both machine NPZs plus the contract-exact two-member `submission.zip` with `compile_bundle`, and run the organizer's `validate_submission.py` against each exact NPZ;
8. only then is a Codabench upload an account action.

The high-value next experiment is to compare the official fixed-name baseline against geometry-moment features on identical **shot-grouped** folds, then ablate Thomson summaries and per-shot normalization. For Award #2, the MAST demo shots can be used as a tiny *diagnostic only*; they are not a substitute for the blind/public-test scorer and must not become a hand-tuned pseudo-training set.

## Truth boundary

Merged source is not a competition result. This carrier performs **no** Codabench registration or upload, Hugging Face credential mutation, paid compute purchase, leaderboard claim, rank claim, award claim, or payment claim. Advertised possible revenue from the two awards is $1,000 total; earned revenue from this carrier remains `$0` until a sponsor actually awards/pays it.
