# KAG-FRONTIER-POLICY

Parent-based policy development with real matched controls. Current candidate is a73,011-byte standalone Kaito v43 derivative. It calls the actual parent agent once, retains the entire production schedule and persistent route/weed state, and changes only sales of observed finished goods. Original market slots for hires, land, feed and seed purchases are preserved. Attribution and Apache-2.0 license accompany it. See RESULTS.md; validation and candidate selection are not yet complete.

```sh
python revenue/kaggriculture/cloud-frontier-policy/build_selected.py
python revenue/kaggriculture/cloud-frontier-policy/test_sales.py
python revenue/kaggriculture/cloud-frontier-policy/measure.py --engine-dir /path/to/existing/engine --seeds 9400137,9400151 --output development.json
```

`candidate.py` exports `agent(observation, configuration=None)` and the final Kaggle entrypoint; only the Python standard library is required. Deploy with LICENSE and NOTICE.md. build.py/overlay.py retain the first rejected Igor experiment; build_selected.py builds the current candidate. Unchanged public parents are in vendor/. All sources were reused from the existing cloud cache; no second simulator or repeated downloads.

measure.py calls the existing process-isolated cloud-eval.play and pinned official interpreter. Passive hooks record per-game actual unit actions, unchanged non-PASS actions, successful market transaction units/cash, terminal farm/inventory, startup and decision timing/resource samples. Total wall time includes instrumentation overhead. It is not hosted Kaggle scoring or a measured rating. No owner PC or paid compute was used.

Development seeds9400109,9400123,9400137,9400151. Reserved selection validation seeds9400203,9400217,9400231,9400249 remain untouched. The selection decision and exact source hash will be frozen before those games.
