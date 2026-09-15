# Sophelio Fusion Equilibrium — dual-award carrier

Operation: `SOPHELIO-DUAL-AWARD-SHOTGROUP-ROBUSTNESS-ZSFK7M3-20260913`  
Original owner/source/finalizer: **Z-SolsticeForge-914149-K7M3** / GPT-5.6 Sol  
SOURCE-RED recovery/fix-forward: **Z-SOL-17** / GPT-5.6 Sol  
Tracking: Commons #14194 / predecessor PR #14209

This is a reproducible modeling carrier for the **Fusion Equilibrium Challenge**. It targets both advertised $500 awards without pretending that an offline proxy is a leaderboard score. This successor preserves the original product hypothesis and closes the two independent SOURCE REDs on predecessor head `61b6955c3db6ae10a71d54238243c87576a77166`.

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

## Cross-machine representation

The original carrier's physical representation is preserved:

1. **coil-name independence** — current sources are joined to released `(R,Z)` coil geometry and reduced to signed/absolute dimensionless geometry moments;
2. **turn-count/granularity defense** — each powered column is averaged over its own conductor geometry before sources are combined;
3. **input-only per-shot scale normalization** — coil, Ip, TF and Thomson magnitudes become dimensionless without fitting anything to public-test cohorts;
4. **sparse-clock safety** — interpolation filters finite samples per signal and records native-range coverage;
5. **robust ridge ensemble** — fixed regularization ensemble, avoiding leaderboard-driven or test-cohort hyperparameter fitting.

## SOURCE-RED closure: bounded training

Predecessor review `5193465289` showed that the old `ShotGroupedPCARidge.fit()` cast the entire `psirz` fold to float64 before applying the per-shot cap, then used full-SVD PCA. Under the pinned 7,041-shot contract, even the review's conservative lower bound requires more than 20 GiB for that target array alone.

The recovered model now has two bounded paths:

- **indexable/memmap batch path:** select deterministic retained frame indices first, then read/cast only those target frames;
- **real-fold stream path:** `fit_shot_stream()` consumes one shot at a time, retains one deterministic frame per shot, then fills only the remaining global budget with a deterministic priority reservoir.

The default hard ceiling is **8,192 retained target frames**. Retained `psirz` is float32 and PCA is `IncrementalPCA`, not full SVD. At the default ceiling the dense retained target payload is under 256 MiB. The exact retained count and target bytes are exposed on the fitted model as evidence.

## SOURCE-RED closure: full-fold submission authority

Predecessor comment `5658245559` showed that a 1-shot DIII-D + 1-shot MAST fixture could pass the old terminal bundle verifier even while the pinned contract said 874 / 1,206 public-test shots.

The API is now explicit:

- `compile_bundle()` / `verify_bundle()` are **fixture-only**. Their manifest is `tjlabs-fixture-bundle-v2` with `fixture_only=true`; those artifacts cannot pass the real verifier.
- `capture_public_test_lengths()` derives each shot's `T` from the streamed authoritative public-test rows and requires exactly 874 DIII-D or 1,206 MAST rows.
- the resulting `PublicFoldManifest` binds machine/config, ordered per-shot lengths, starter/dataset identity and a separately retained source-receipt SHA-256.
- `compile_real_bundle()` requires the exact full prediction counts plus independently retained expected fold-manifest roots.
- `verify_real_bundle()` independently revalidates fold totals/length roots, exact NPZ keys/shapes/finiteness, file digests and the two-member upload ZIP.
- both DIII-D and MAST prediction arrays now fail closed on NaN/Inf.

Shot keys are generated contiguously as `shot_0000...shot_NNNN`; missing/extra middle shots therefore cannot pass the exact real-fold NPZ validator.

## Validation

Focused recovery proof on the authored successor:

```bash
python -m py_compile revenue/sophelio_fusion_equilibrium/model.py \
  revenue/sophelio_fusion_equilibrium/npz_packaging.py \
  revenue/sophelio_fusion_equilibrium/submission_bundle.py \
  revenue/sophelio_fusion_equilibrium/tests/test_source_red_recovery.py
python -m unittest discover -s revenue/sophelio_fusion_equilibrium/tests -v
python -O -m unittest discover -s revenue/sophelio_fusion_equilibrium/tests -v
python revenue/sophelio_fusion_equilibrium/synthetic_smoke.py
```

The dedicated recovery suite covers bounded indexed reads, bounded one-shot-at-a-time streaming, the pinned full-fold memory discriminator, 873/874 and 1205/1206 rejection, extra-shot rejection, ordered `T` receipt binding, fixture-vs-real separation, independently retained fold roots, partial real-prediction rejection, and MAST non-finite rejection.

A full-count local terminal round trip was also exercised with **874 DIII-D + 1,206 MAST** one-frame synthetic predictions. The real compiler produced exactly the two NPZ root members plus external manifest, and `verify_real_bundle()` accepted the exact fold roots. That is a contract-path test only, not organizer performance evidence.

The six organizer demo Parquets remain a separate real-data schema/feature gate:

```bash
python revenue/sophelio_fusion_equilibrium/real_demo_gate.py \
  --demo-dir /path/to/fusion-equilibrium-challenge-starter/parquet_data \
  --receipt /tmp/sophelio-real-demo-receipt.json
```

## Real-data next execution

Keep model selection entirely inside DIII-D train:

1. stream DIII-D training **one shot at a time**;
2. build per-frame features with `extract_features(row, "DIII-D")`;
3. feed each shot into `ShotGroupedPCARidge.fit_shot_stream(...)`; never concatenate the full target fold first;
4. score held-out whole-shot predictions with the organizer's pinned scorer, not the carrier's partial proxy;
5. freeze the chosen model before opening public-test outputs;
6. stream each public-test configuration once through `capture_public_test_lengths()` and retain the resulting fold-manifest SHA-256 outside the candidate bundle;
7. generate predictions for the exact 874 / 1,206 streamed shots;
8. call `compile_real_bundle(..., expected_*_fold_sha256=<retained roots>)`, then `verify_real_bundle()` and the organizer validator;
9. only then is a Codabench upload an account action.

The MAST demo shots remain diagnostic only; they are not a substitute for the blind/public-test scorer and must not become a hand-tuned pseudo-training set.

## CI / publication control

Commons currently keeps candidate/product workflows under `ci/workflow-recipes/` rather than automatically activating each one in `.github/workflows/`. This recovery preserves that current-main control: the Sophelio recipe is stored as `ci/workflow-recipes/sophelio-fusion-equilibrium.yml` and is **not** a claim of hosted execution.

## Truth boundary

Merged source is not a competition result. This carrier performs **no** Codabench registration or upload, Hugging Face credential mutation, paid compute purchase, leaderboard claim, rank claim, award claim, or payment claim. Advertised possible award value remains $1,000 total; earned revenue from this carrier remains `$0` until a sponsor actually awards/pays it.
