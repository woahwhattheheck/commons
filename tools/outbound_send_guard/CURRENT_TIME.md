# Current-time outbound send preflight

`current.py` is the supported current-use boundary for the outbound send guard. All positive preflight decisions are bound to verifier-owned process UTC. Caller-authored intent/evidence timestamps are evidence inputs, never the source of present-time authority.

## Architecture

- `_guard_core.py` is the byte-preserved deterministic v1 engine used only as an underscore-private implementation dependency and by focused historical engine tests.
- `current_impl.py` is the byte-preserved verifier-clock implementation from the repaired #14333 source head.
- `current.py` binds `current_impl` to `_guard_core` internally and exposes safe current/historical APIs without exposing the private core as `current.guard.evaluate`.
- `guard.py` preserves legacy parsing/helper imports but deliberately excludes the old positive `evaluate` and `main`; its supported evaluation and CLI paths route to `current.py`.
- `guard_legacy.py` is an explicit historical compatibility surface. Its evaluator requires `historical_at` and returns only `HISTORICAL_INTEGRITY_ONLY` / `HOLD`; its CLI is permanently non-authorizing.

## Current contract

```python
from tools.outbound_send_guard import compile_current, verify_current

receipt = compile_current(intent_object, evidence_object)
verification = verify_current(intent_object, evidence_object, receipt)
```

There is no current API clock parameter and no CLI `--as-of` option. Before every positive authority operation the wrapper reinstalls a process-UTC clock and the private core captured at definition time; rebinding `current._utc_now` or `current_impl._utc_now` cannot select verifier time. Current compiler/verifier emitters sample that owned process UTC inside the authority operation. The code-owned ceilings are 900 seconds evidence age, 900 seconds request age, 300 seconds future skew, and 60 seconds positive receipt lifetime; candidate policy may tighten but never widen them.

The current receipt binds source custody, core receipt, verifier time, expiry, policy generation, current decision, and historical decision. Verification reconstructs the bound receipt at its original verifier time, then rechecks semantics under fresh process UTC. Expiry, changed sources, reseal, or decision drift clears no current authority.

Every compiler/verifier result keeps `side_effects_authorized=false`.

## Historical replay

`compile_historical_at()` exists only for deterministic reconstruction. It emits the distinct historical schema, mode `HISTORICAL_INTEGRITY_ONLY`, outward `decision=HOLD`, and all current/reply/net-new clear bits false even when the historical core decision is `ALLOW_NEW` or `REPLY_ONLY`.

The predecessor compatibility defect is closed: supported `guard.evaluate(...)` no longer exposes the historical core. A stale matched intent/evidence pair can be reconstructed only through the explicitly historical/internal path, while both package `evaluate` and compatibility `guard.evaluate` reassess it against verifier-owned current time and HOLD.

## CLI

```bash
python -m tools.outbound_send_guard compile --intent intent.json --evidence evidence.json --out receipt.json
python -m tools.outbound_send_guard verify --intent intent.json --evidence evidence.json --receipt receipt.json --out verification.json
python -m tools.outbound_send_guard.guard --intent intent.json --evidence evidence.json --out receipt.json
```

All three supported routes are current-time bound. `python -m tools.outbound_send_guard.guard_legacy` is intentionally non-authorizing and returns HOLD.

## Regression requirement

Hosted CI must compile the private core, safe wrappers, byte-preserved current implementation, and tests, then run the deterministic/core and current/compatibility suites on Python 3.11 and 3.13 in both normal and `python -O` modes. A head change invalidates prior execution/review evidence.
