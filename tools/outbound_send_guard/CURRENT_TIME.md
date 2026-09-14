# Current-time outbound send preflight

`current.py` is the supported **current-use** boundary for the outbound send guard. The original `guard.py` decision engine remains deterministic and useful for historical reconstruction, but its two input timestamps are caller data and cannot by themselves establish that a snapshot is fresh now.

## Current contract

Production callers use:

```python
from tools.outbound_send_guard import compile_current, verify_current

receipt = compile_current(intent_object, evidence_object)
verification = verify_current(intent_object, evidence_object, receipt)
```

or the exact-byte equivalents. The compiler samples process UTC. There is no public current API clock parameter and no CLI `--as-of` option.

The current wrapper:

- snapshots parsed caller objects once before semantic evaluation;
- keeps exact consumed-byte custody separate from canonical-object custody;
- preserves the deterministic core decision and receipt;
- checks both `intent.requested_at` and `evidence.generated_at` against verifier time;
- caps evidence age at 900 seconds, request age at 900 seconds, and future skew at 300 seconds even when candidate policy is wider;
- lets candidate policy tighten those limits, never widen them;
- gives a positive receipt a maximum 60-second lifetime;
- binds `verified_at`, `valid_until`, policy generation, source custody, and core receipt into a new content address;
- replays the receipt at its bound verifier time before reassessing it under fresh process UTC;
- keeps `side_effects_authorized=false` in every compiler and verifier result.

`ALLOW_NEW` clears only the net-new preflight prerequisite. `REPLY_ONLY` clears only the reply prerequisite. Neither result performs or proves a provider mutation. A lease, relationship/route controls, current provider reread, customer-link checks, and the exact one-shot send consumer remain separate mandatory boundaries.

## Historical replay

`compile_historical_at()` exists for deterministic reconstruction. Its receipt is permanently labeled `HISTORICAL_INTEGRITY_ONLY`, sets the outward decision to `HOLD`, and cannot clear current preflight even when the historical core decision was `ALLOW_NEW`.

## CLI

Use the package CLI, not the deterministic engine module:

```bash
python -m tools.outbound_send_guard compile \
  --intent intent.json \
  --evidence evidence.json \
  --out receipt.json

python -m tools.outbound_send_guard verify \
  --intent intent.json \
  --evidence evidence.json \
  --receipt receipt.json \
  --out verification.json
```

The CLI consumes one bounded, no-follow, single-link regular-file generation, verifies that the visible path still names the consumed inode, and creates outputs exclusively. Existing outputs and final-component symlinks are refused.

Exit codes: compile uses `0 ALLOW_NEW`, `3 REPLY_ONLY`, `4 HOLD`, `5 DO_NOT_RESEND`, `2 invalid input or I/O failure`. Verify returns `0` only for an unexpired positive receipt whose current decision still matches; `5` for current `DO_NOT_RESEND`; otherwise `4`, with malformed/tampered input at `2`.

## Regression gate

```bash
python -m py_compile \
  tools/outbound_send_guard/current.py \
  tools/outbound_send_guard/test_current.py
python -m unittest -v \
  tools.outbound_send_guard.test_guard \
  tools.outbound_send_guard.test_current
python -O -m unittest -v \
  tools.outbound_send_guard.test_guard \
  tools.outbound_send_guard.test_current
```

The hostile suite includes matched stale timestamps, matched future timestamps, one-sided stale intent/snapshot, candidate policy widening, expiry, verifier-time tamper with reseal, changed source bytes, exact-byte custody, caller mutation after snapshot, create-exclusive output, and symlink refusal.
