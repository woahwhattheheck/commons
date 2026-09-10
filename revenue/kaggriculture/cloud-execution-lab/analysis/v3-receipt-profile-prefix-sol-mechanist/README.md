# TITAN V3 receipt-profile executable-prefix closure

`SellScheduler.receipt_profile()` is a physical-capacity oracle for the SELL
optimizer.  It replays future market rows to decide whether delaying a target
sale can keep the shed below its reserve boundary.

The frozen scheduler replays **every authored market row**.  The pinned official
interpreter first truncates each action to:

```python
q[:max(1, int(maxMarketOrdersPerTurn))]
```

A row beyond that raw prefix is inert.  Treating it as executed can change
projected shed stock, actor cardinality, and the resulting `capacity_ok`
decision.

## Exact predecessor

At step 0:

- shed: `CARROT=1`, `MELON=98` (99/100 total);
- farmer inventory: `WHEAT=1`;
- market cap: one row;
- market queue: `[[], ["SELL", "MELON", 1]]`;
- step 1 farmer action: `DROP`;
- candidate target sale: defer the one CARROT until step 1.

The frozen projection subtracts the suffix MELON sale, then applies the DROP:
`99 - 1 + 1 = 99`, so the deferred plan passes.

The official engine executes only the empty row at index 0.  Its shed remains
99 after market and reaches 100 on the next DROP.  The reserve predicate
requires at most 99 before the target sale, so the same plan must fail.

The focused contracts execute the pinned engine's real `_process_market()` and
`_apply_unit_action()` for that witness.  They also extract and execute both the
frozen and materialized `receipt_profile()` methods.

## Repair

The materialized candidate adds one helper mirroring the interpreter's raw
queue construction and routes only the `receipt_profile()` market replay
through it.  Both current and future action rows use the same helper.

The packet deliberately does not change:

- `cash_reserve()` or purchase affordability/fill;
- atomic PLANT handling;
- HIRE funding semantics;
- SELL targets, quantities, priority, objective, or defaults;
- canonical runtime/config/archive/release pointers.

It is an additive source handoff.  Strength remains
`SOURCE_REAL_ACTION_UNMEASURED` until an owner composes it into a current tree
and runs returned-action-bound paired evidence.

## Binding

- base commit: `2e2e7e52fd2d5c62117ac49c7f1eabb505078ffb`
- scheduler Git blob: `a483b24dd72b580d7d8811636b54d2d44f391575`
- official engine Git blob: `3c202c7ee921da239356789e266b694635103fc4`
- coordination issue: `#12006`

The materializer rejects source/engine drift, requires both official prefix
anchors exactly once, applies one helper insertion and one call-site
replacement, compiles the candidate, rejects path/inode/symlink aliases, writes
atomically, and re-reads all bound bytes.  Its JSON receipt contains no
workspace-specific paths.

## Run

From this directory:

```bash
python -m py_compile materialize.py test_materialize.py
python -m unittest -v test_materialize.py

tmp="$(mktemp -d)"
python materialize.py \
  ../../scheduler.py \
  ../../reference/engine/kaggriculture.py \
  "$tmp/scheduler.py" > "$tmp/receipt.json"
python -m py_compile "$tmp/scheduler.py"
```
