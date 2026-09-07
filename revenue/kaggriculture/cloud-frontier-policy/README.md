# KAG-FRONTIER-POLICY

Development checkpoint: standalone Igor-derived candidate with observation-based finished-goods sales. Not yet a submission recommendation. Uses the existing official pinned evaluator; no second simulator or new source downloads.

Run from Commons:

```sh
python revenue/kaggriculture/cloud-frontier-policy/build.py
python revenue/kaggriculture/cloud-frontier-policy/measure.py --engine-dir /path/to/existing/engine --seeds 9400109,9400123 --output development.json
```

`candidate.py` exports `agent(observation, configuration=None)` and the final Kaggle entrypoint. It needs only the Python standard library. Deploy with LICENSE and NOTICE.md. Results include per-game terminal cash, action counts, unchanged non-PASS actions, actual successful market transaction units/cash, terminal farm/inventory and process startup/decision/resource measurements. Passive diagnostic hooks add driver overhead, so total wall time includes diagnostics; agent child timing is separately recorded.

Development seeds: 9400109, 9400123. Reserve 9400203, 9400217, 9400231, 9400249 for the selected candidate; do not inspect those episodes while choosing changes. Read RESULTS.md for measured selection status when published.
