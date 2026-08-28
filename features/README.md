# Feature tracker records

Append-only machine-readable registry for the public feature tracker.

- `registry/{id}.json` — one file per feature. New files merge. Do not overwrite.
- `evidence/{id}.json` — one file per evidence row. New files merge. Do not overwrite.

Schema and status rules: [ground/FEATURE_TRACKER.md](../ground/FEATURE_TRACKER.md).

Generator:

```
python3 host/feature_tracker.py --write
python3 test_feature_tracker.py
```

Public doors: [feature-tracker.html](../feature-tracker.html) · [feature-tracker.json](../feature-tracker.json)

`features.html` at repo root is the FEATURES board lane. Do not remint it.
