# Experiment ledger

`host/experiment_ledger.py` implements visibility-plan D1: one deterministic row per **hypothesis id**, with the four evidence stages visible side by side under one declared objective.

Every hypothesis declaration contains an immutable statement and objective (`metric`, `direction`, `unit`, and optional finite `threshold`). The ledger always carries exactly these four benches:

- `forensic_estimate`
- `small_gate`
- `field_gate`
- `frozen_panel`

Each bench records its state, sample size, numeric metrics, evidence references, and an optional panel id. `NOT_EXECUTED` uses `sample_size: null`; it never invents zero observations. Terminal `COMPLETE` or `INVALID` records require a positive sample size and are immutable. A `RUNNING` record may advance to a terminal record but its observed sample size cannot decrease.

This is deliberately not the promotion policy. D1 records evidence under the declared objective; a separate disposition layer decides whether that evidence means promote, hold, or drop. The ledger therefore does not turn a positive mean into approval, collapse a missing bench into zero, or treat an evidence reference as proof that remote bytes were independently revalidated.

The parser rejects duplicate JSON keys, NaN/Infinity, boolean-as-number coercion, missing benches, unknown fields, and non-finite numeric metrics. Writes are deterministic and atomic on the local filesystem.

Example:

```bash
python host/experiment_ledger.py add experiments.json H3c \
  --statement 'goose rescue improves margin' \
  --objective-json '{"metric":"margin_delta","direction":"maximize","unit":"points"}'

python host/experiment_ledger.py record experiments.json H3c small_gate \
  --record-json '{"state":"COMPLETE","sample_size":32,"metrics":{"mean_delta":12.5},"panel":"seeds-6101-6132","evidence":["run:123"]}'

python host/experiment_ledger.py validate experiments.json
python host/experiment_ledger.py get experiments.json H3c
```
