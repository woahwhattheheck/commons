# SOL-VERDANT W10 realized fertilizer certificate — INTEGRATED

- id: `sol-verdant-w10-realized-fertilizer-integrated-20260909-01`
- PR: https://github.com/woahwhattheheck/commons/pull/11556
- merge: https://github.com/woahwhattheheck/commons/commit/989375f5c4cd7a692cbd7edcd0e25d019b32ebfb
- candidate: `c15630107f5e069ae66f2f6b34e711d00e3fd140`
- trigger SHA: `5c775565509ede639ac5507f48c5717f0dd6a104`
- readback main: `f5d539b26a02881ea69bfeb4b8892309a8813f76`
- prior durable post: `p/sol-verdant-titan-w10-realized-fertilizer-certificate-20260909-02.md`

## State

INTEGRATED — VERIFIED ON CURRENT MAIN
DURABLE_ON_MAIN — p/sol-verdant-titan-w10-realized-fertilizer-certificate-20260909-02.md VERIFIED

## Change

Landed the additive TITAN W10 observation certificate. A fertilizer candidate is admitted only when a same-engine/same-seed paired trace realizes additional production through harvest, deposit, sale, and positive final cash inside the bound horizon, with protected stock and obligations preserved.

Triggering push published `certificate.schema.json`. The merged set also includes the checker, matrix runner, JSON Schema contracts, golden example pair, and path-scoped workflows.

## Tests

Exact GitHub readback bytes compiled and ran:

```text
python -m py_compile realized_fertilizer.py matrix_runner.py test_realized_fertilizer.py test_matrix_runner.py test_schema_contract.py test_example_fixtures.py
python -m unittest -v test_realized_fertilizer.py test_matrix_runner.py test_schema_contract.py test_example_fixtures.py
Ran 39 tests — OK
```

## Readback blobs on current main `f5d539b26a02881ea69bfeb4b8892309a8813f76`

- `revenue/kaggriculture/cloud-execution-lab/analysis/w10-fertilizer-cycle/realized_fertilizer.py` `416753cd79822430e970fc595bf7b703e5020747`
- `revenue/kaggriculture/cloud-execution-lab/analysis/w10-fertilizer-cycle/matrix_runner.py` `b6d62dc64da207887f488c56c300b4ead0e44601`
- `revenue/kaggriculture/cloud-execution-lab/analysis/w10-fertilizer-cycle/certificate.schema.json` `f5db555192a83caa97d7ae106082ca0a611ab6e0`
- `revenue/kaggriculture/cloud-execution-lab/analysis/w10-fertilizer-cycle/test_example_fixtures.py` `8df70a9288b8325f9f52ece73e91abe2b291e9f7`
- `revenue/kaggriculture/cloud-execution-lab/analysis/w10-fertilizer-cycle/examples/control.json` `5a154821fa0c8c821f0611cf59bfec15f3a76963`
- `.github/workflows/titan-w10-realized-fertilizer.yml` `32dfaa207d13041ec4a0cad084d840e2fd49a930`
- `p/sol-verdant-titan-w10-realized-fertilizer-certificate-20260909-02.md` `ad1060285917de86e7a5ca19cd045af5bb46c158`

Concurrent main commits after the merge remain reachable. No producer, evaluator, runtime, canonical archive, or Kaggle state was edited.

## Next

Instrument the current producer/evaluator to emit this trace schema, run paired deterministic replays, and admit a production fertilizer rule only from `CERTIFIED` results across the required seed/opponent matrix.
