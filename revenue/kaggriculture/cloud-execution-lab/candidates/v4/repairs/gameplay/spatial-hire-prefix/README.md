# SpatialTempo executable-HIRE boundary repair

One source-only component in `main:candidates/v4`, not another V4 runtime or controller.

## Mechanism and disposition

Current native `spatial_tempo.py` scans complete selected and authored future market vectors for `HIRE`. The official interpreter executes only the raw prefix `market[:max(1, int(maxMarketOrdersPerTurn))]` (default 10). A HIRE in the inert suffix therefore blocks an otherwise certified weed-clearing BUILD/PLANT continuation even though no worker can spawn.

This exact-source transformer applies that prefix to both existing boundary scans. Empty/PASS/zero-sale slots still consume capacity: no filtering before slicing. Every executable HIRE remains a boundary. Existing retry witnesses, seed/service checks, rejoin logic, emission and raw authored market vectors remain unchanged. The existing continuation mechanism can then act where it was incorrectly vetoed; this is not action-equivalent in those constructed worlds.

**Source-ready, not activated.** The pristine current native parent has four routes and 2,880 authored rows, with zero HIRE rows beyond the default raw cap of ten. The packet proves correctness on constructed/composed inputs, not natural engagement, final-game profit or playing strength. Do not activate merely because these tests pass. Production source, defaults, archives and Kaggle remain unchanged.

## Authenticated inputs

Use existing GitHub Actions artifact `10175943272` from `woahwhattheheck/commons`, not a newly dispatched run. Its ZIP SHA256 is `3a3b74936d238bf884f89a1b279f42676cda35c590f131a6a3548de52d61b4e8`. The embedded `checked-package/exports/titan-current.tar.gz` is 429,604 bytes and SHA256 `b567942e4fb4e0571ebf9f8eaaf143d4a9156df3289f09a98db37823ef4d68d9`.

Extract into a dedicated pristine directory. The runner authenticates SOURCE.json, all 109 runtime-map files and explicit engine/evaluator pins before importing package code. SOURCE.json SHA256: `e87d70dd3bcf5aea1e929f1a5dbdc86f3cc33d8a0b3492986f2970fc8e774be2`. Exact official engine Git blob: `3c202c7ee921da239356789e266b694635103fc4`.

## Execute

From this component directory, with an absolute path to that pristine extraction:

```sh
export TITAN_PACKAGE=/absolute/path/to/pristine-b567
python test_spatial_hire_prefix.py
python -O test_spatial_hire_prefix.py
python spatial_hire_prefix.py "$TITAN_PACKAGE/spatial_tempo.py" /separate/staging/spatial_tempo.py
```

The staging output must not exist. The transformer rejects source drift and repeated application, also under `-O`; it never patches production in place. If a peer has changed the source, recompose the two-scan semantics on that new source and rerun the evidence instead of relaxing the input pin or replacing their complete module.

To repeat the surrounding regressions, make two separate copies of the pristine package, replace only spatial_tempo.py in the candidate copy using the staged output, then run the following from each package root with normal Python and again with `python -O`:

```sh
PYTHONPATH=.:checks python -m unittest checks.test_weed_continuation checks.test_idle_fertilizer checks.test_crop_release checks.test_operating_stock checks.test_feed_stock -q
```

## Executed evidence

Nine focused tests pass in normal and optimized modes. Each mode executes 600 full official-interpreter callbacks: 72 suffix/truncation pairs, 24 live-HIRE positive controls, and 24 three-arm six-callback BUILD/PLANT worlds across both seats. The repaired and truncated-reference worlds have identical complete observations/actions; the unmodified raw baseline misses the build or watered crop. Final cash and actor positions agree. All five deliberate boundary mutants fail, including either unbounded scan, cap off-by-one, filter-before-cap and a zero minimum.

The surrounding 118-test run yields **117 passes and the same one existing failure** for pristine and candidate packages, in both normal and optimized modes. This is not a clean full-suite pass. The failure is `IdleFertilizerRuntimeTests.test_prelude_fallback_returns_and_sells_already_collected_unit`: prelude fallback returns PASS instead of SOUTH. It was relayed to the existing terminal-fallback owner, not absorbed into a competing repair. RECEIPT.json contains the six full logs, exact input/output identities, mutant counts and scope limitations.

## Single-tree handoff

The sole current-runtime assembler may consume this component after deciding whether composed/nondefault-cap engagement justifies it, composing with newer source and retaining package/fallback/competitive gates. Do not execute a legacy V4 materializer, change a default, or replace another spatial/idle-fertilizer/crop continuation. This claim is complete when these files are on canonical main; no outstanding build demand is created by this packet.
