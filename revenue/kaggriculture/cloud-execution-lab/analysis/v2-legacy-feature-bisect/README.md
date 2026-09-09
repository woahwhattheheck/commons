# Submitted V2 legacy-feature bisect

This lane tests the two feature activations that were present in submitted TITAN V2 (`e3631250…`) but absent from submitted V1 (`7b58fa06…`): `redundant_hire` and `market_pressure`.

It does **not** modify the canonical controller, release archive, default configuration, Kaggle notebook, or submission. The experiment starts from the byte-exact submitted-V2 archive and creates three variants by changing only `TITAN-CONFIG.json`:

- `no_redundant_hire`
- `no_market_pressure`
- `no_legacy_features`

The paired panel is 4 variants × 4 source-pinned public opponents × 4 fresh environment seeds × both seats = **128 complete official-engine games**. Each two-game shard has a signed receipt binding the exact candidate tree, config, evaluator, loader, engine, opponent, seed, resource limits, raw report, and invocation. Resume accepts a shard only after validating that receipt and the full 719-action trace contract.

## Result

`market_pressure` should remain enabled on this panel: mean enabled margin effect **+252.0625** over 32 exact paired cells. `redundant_hire` is economically negligible here: **+3.5** mean effect. Every variant won all 32 games, so neither legacy activation is supported as the cause of the hosted V2 regression; the source-pinned public panel is distribution-misaligned with that leaderboard failure.

See `RESULTS.md` for the human-readable report, `SUMMARY.json` for the machine-readable verdict, `PAIRED-CELLS.csv` for every exact feature comparison and trace hash, `SHARD-HASHES.csv` for all 64 report/receipt identities, `ISOLATION.json` for byte-isolation proof, and `HARNESS.json` for evaluator identity.

## Verify the implementation

```bash
python3 -m unittest -v test_run_bisect.py
python3 -m py_compile run_bisect.py test_run_bisect.py
```

## Reproduce the panel

```bash
python3 run_bisect.py \
  --source-archive /path/to/titan-submitted-v2-e363.tar.gz \
  --harness-root /path/to/titan-v1-predecessor-public-policy-gauntlet-20260909 \
  --work-dir ./work \
  --seeds 2609098601,2609098602,2609098603,2609098604 \
  --opponents arlene,apex,reyhan,kaito \
  --run-variants baseline,no_redundant_hire,no_market_pressure,no_legacy_features \
  --jobs 4
```

The runner rejects path-traversal/link archives, non-config byte drift, wrong source/harness hashes, incomplete or mislabeled reports, duplicate/missing seat cells, stale receipts, mutated evidence, and partial grids.
