# SpatialTempo executable-HIRE boundary repair

One source-only component in `main:candidates/v4`, not another V4 runtime or controller.

## Mechanism and disposition

Current native `spatial_tempo.py` scans complete selected and authored future market vectors for `HIRE`. The official interpreter executes only a raw market prefix governed by `maxMarketOrdersPerTurn` (default 10). A HIRE in the inert suffix therefore blocks an otherwise certified weed-clearing BUILD/PLANT continuation even though no worker can spawn.

This exact-source transformer applies the executable prefix to both existing boundary scans. Empty/PASS/zero-sale slots still consume capacity: no filtering before slicing. Every executable HIRE remains a boundary. For authority safety, the transformer now consumes `maxMarketOrdersPerTurn` only when it is a plain Python `int`; boolean, float, string or other malformed cap values fail closed by returning the inherited selected action without opening a SpatialTempo continuation. Missing cap still uses the documented integer default 10. Existing retry witnesses, seed/service checks, rejoin logic, emission and raw authored market vectors remain unchanged.

**Source-ready, not activated.** The pristine current native parent has four routes and 2,880 authored rows, with zero HIRE rows beyond the default raw cap of ten. The packet proves correctness on constructed/composed inputs, not natural engagement, final-game profit or playing strength. Do not activate merely because these tests pass. Production source, defaults, archives and Kaggle remain unchanged.

## Authenticated inputs

Use existing GitHub Actions artifact `10175943272` from `woahwhattheheck/commons`, not a newly dispatched run. Its ZIP SHA256 is `3a3b74936d238bf884f89a1b279f42676cda35c590f131a6a3548de52d61b4e8`. The embedded `checked-package/exports/titan-current.tar.gz` is 429,604 bytes and SHA256 `b567942e4fb4e0571ebf9f8eaaf143d4a9156df3289f09a98db37823ef4d68d9`.

Extract into a dedicated pristine directory. The runner authenticates SOURCE.json, all 109 runtime-map files and explicit engine/evaluator pins before importing package code. SOURCE.json SHA256: `e87d70dd3bcf5aea1e929f1a5dbdc86f3cc33d8a0b3492986f2970fc8e774be2`. Exact official engine Git blob: `3c202c7ee921da239356789e266b694635103fc4`.

## Execute

From this component directory, first run the dependency-light strict-custody regression, then run the authenticated b567 suite:

```sh
python -B -m unittest -v test_strict_market_limit.py
python -O -B -m unittest -v test_strict_market_limit.py
python -m py_compile spatial_hire_prefix.py test_strict_market_limit.py test_spatial_hire_prefix.py

export TITAN_PACKAGE=/absolute/path/to/pristine-b567
python -B test_spatial_hire_prefix.py
python -O -B test_spatial_hire_prefix.py
python spatial_hire_prefix.py "$TITAN_PACKAGE/spatial_tempo.py" /separate/staging/spatial_tempo.py
```

The staging output must not exist. The transformer rejects source drift and repeated application, also under `-O`; it never patches production in place. If a peer has changed the source, recompose the two-scan semantics on that new source and rerun the evidence instead of relaxing the input pin or replacing their complete module.

To repeat the surrounding regressions, make two separate copies of the pristine package, replace only `spatial_tempo.py` in the candidate copy using the staged output, then run the following from each package root with normal Python and again with `python -O`:

```sh
PYTHONPATH=.:checks python -m unittest checks.test_weed_continuation checks.test_idle_fertilizer checks.test_crop_release checks.test_operating_stock checks.test_feed_stock -q
```

## Evidence generations

`RECEIPT.json` is immutable predecessor evidence for the original executable-prefix repair generation. It records nine focused tests per mode, 600 full official-interpreter callbacks per mode, five killed boundary mutants, and the identical pre-existing IdleFertilizer surrounding-suite failure. It must **not** be interpreted as exact-head evidence for the later strict market-cap authority closure.

The strict-authority successor adds an independent dependency-light test plus a tenth authenticated test in `test_spatial_hire_prefix.py`. Plain integer caps retain the predecessor worlds. Coercible non-integers (`"2"`, `2.9`, `False`, `True`) are now explicit fail-closed cases, and the mutation battery adds a sixth mutant that restores `int(...)` coercion; that mutant must be killed. Until a repo-mounted executor reruns the exact successor bytes against the pinned b567 package, this generation remains **HOLD / pending exact-head execution** and its manifest must not claim the predecessor receipt as current validation.

The predecessor surrounding 118-test run yielded **117 passes and the same one existing failure** for pristine and candidate packages, in both normal and optimized modes. The failure was `IdleFertilizerRuntimeTests.test_prelude_fallback_returns_and_sells_already_collected_unit`: prelude fallback returned PASS instead of SOUTH. That failure belongs to the existing terminal-fallback lane and is not absorbed into this repair.

## Single-tree handoff

The sole current-runtime assembler may consume this component only after the strict successor is revalidated and its manifest is rotated to the exact successor identities. Compose with newer source and retain package/fallback/competitive gates. Do not execute a legacy V4 materializer, change a default, or replace another spatial/idle-fertilizer/crop continuation. No sibling controller or second V4 is authorized by this package.