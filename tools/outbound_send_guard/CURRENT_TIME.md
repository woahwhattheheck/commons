# Current-time outbound send preflight

`current.py` is the supported **current-use** boundary for the outbound send guard. The deterministic v1 decision engine is retained byte-for-byte in `guard_legacy.py` for historical reconstruction and composed controls, but its two input timestamps are caller data and cannot by themselves establish that a snapshot is fresh now.

`guard.py` is a compatibility facade: it exposes the deterministic helper surface to existing internal callers, while its command-line entrypoint routes old and new CLI syntax through `current.py`. There is no supported command that emits a caller-clock current receipt.

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

Direct Python imports of `guard.evaluate` preserve the deterministic engine for internal composition. They are not the advertised package API: package-level `evaluate` is `compile_current`. Tests pin this distinction so old matched timestamps may remain reproducible as historical engine evidence but cannot pass the package/current boundary.

## CLI

Both package and compatibility module invocations are current-time bound:

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

# Old syntax is accepted only as a current compile compatibility route:
python -m tools.outbound_send_guard.guard \
  --intent intent.json \
  --evidence evidence.json \
  --out receipt.json
```

The CLI consumes one bounded, no-follow, single-link regular-file generation, verifies that the visible path still names the consumed inode, and creates outputs exclusively. Existing outputs and final-component symlinks are refused.

Exit codes: compile uses `0 ALLOW_NEW`, `3 REPLY_ONLY`, `4 HOLD`, `5 DO_NOT_RESEND`, `2 invalid input or I/O failure`. Verify returns `0` only for an unexpired positive receipt whose current decision still matches; `5` for current `DO_NOT_RESEND`; otherwise `4`, with malformed/tampered input at `2`.

## Regression gate

```bash
python -m py_compile \
  tools/outbound_send_guard/guard_legacy.py \
  tools/outbound_send_guard/guard.py \
  tools/outbound_send_guard/current.py \
  tools/outbound_send_guard/test_guard.py \
  tools/outbound_send_guard/test_current.py \
  tools/outbound_send_guard/test_current_entrypoint.py
python -m unittest -v \
  tools.outbound_send_guard.test_guard \
  tools.outbound_send_guard.test_current \
  tools.outbound_send_guard.test_current_entrypoint
python -O -m unittest -v \
  tools.outbound_send_guard.test_guard \
  tools.outbound_send_guard.test_current \
  tools.outbound_send_guard.test_current_entrypoint
```

The hostile suite includes matched stale timestamps, matched future timestamps, one-sided stale intent/snapshot, candidate policy widening, expiry, verifier-time tamper with reseal, changed source bytes, exact-byte custody, caller mutation after snapshot, compatibility CLI routing, create-exclusive output, and symlink refusal.
