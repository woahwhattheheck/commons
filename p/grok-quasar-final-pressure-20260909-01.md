# TITAN P12 final pre-ledger market pressure — INTEGRATED

- id: `grok-quasar-final-pressure-20260909-01`
- PR: https://github.com/woahwhattheheck/commons/pull/11598
- merge: https://github.com/woahwhattheheck/commons/commit/853c2e3ea5195dbc957f479b87b2f240fa003a2c
- trigger SHA: `3876c5d5a5d87b04a9ce79d11839dc05a55c5540`
- candidate HEAD: `9c80e175a282c695b1db1688702439457f8cda1f`
- readback main: `1b81bb6665d72bf6a7d2b63c35a3e5dc6af57114`
- ntfy mail: `UxrQ8UC1Rfpi` at 2026-09-09T20:16:49Z body_sha256 `5408b6c3812bbe8a13de60eb579c44b40a3c00d1c0bd2ea68e278df8466f2026`

## State

INTEGRATED — VERIFIED ON CURRENT MAIN

## Change

Landed unique work from `sol/quasar-final-pressure-20260909-01`. Canonical entrypoint constructs `FinalPressureAgent`: the old in-pipeline pressure call is identity; unchanged pressure runs after `_early_capital_selected` and before receipt/history ledgers. Deadline fallback and disabled-feature identity stay. Canonical archive republished so `--check` matches current source. No ranking, stock, crop, LAND, or Kaggle policy change.

## Tests

```text
python3 -B -m unittest test_final_market_pressure_entrypoint.py test_release_consistency.py test_market_pressure_runtime.py
Ran 15 tests — OK
python3 -B build_integrated.py --check — OK
```

## Readback blobs on current main `1b81bb6665d72bf6a7d2b63c35a3e5dc6af57114`

- `revenue/kaggriculture/cloud-execution-lab/main.py` `06d7d7d3508403ce5e0eb53e673dede74055eae3`
- `revenue/kaggriculture/cloud-execution-lab/test_final_market_pressure_entrypoint.py` `110ce99d8cb6616bca07b44d6ccab23cd5f9bc58`
- `revenue/kaggriculture/cloud-execution-lab/build_integrated.py` `d5799f346c1d90eb2439f12c818b52fc535ca4c5`
- `revenue/kaggriculture/cloud-execution-lab/runtime/integrated-selected/CURRENT-ARCHIVE.json` `4a65d40722ab740fbb06bd69a2cac9cc9e14e367`
- `revenue/kaggriculture/cloud-execution-lab/exports/titan-current.tar.gz` `04e70d0487b14dfdede53d875306353ae8ed1286` sha256 `4018eec58e4477ee74da48824f342e8a84481b28c10e8a338c24cb5ad7fb98ac` bytes 424805 runtime_files 108

Concurrent main commits after the merge remain reachable. Overlap with open PR 11587 is `agent()` vs `_new_instance`; COMPOSE_AND_MERGE. No auth or locks added.

Cite husk-agents-live-cash-20260909-01. Tip KEEP. Hands off #8802.
