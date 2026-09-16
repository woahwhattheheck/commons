# Outbound send guard

`tools/outbound_send_guard` is a read-only, offline preflight for parallel sales and email workers. It exists because a workspace-only search can say “no send receipt” while the mailbox already contains a provider-SENT message to the buyer. A second worker must not turn that visibility gap into duplicate outreach.

The package does not search Gmail or Slack and cannot send email. An adapter/operator supplies an `outbound-send-intent/v1` and a complete `outbound-send-evidence/v1` snapshot.

## Supported current boundary

Use the package API or package CLI:

```python
from tools.outbound_send_guard import compile_current, verify_current

receipt = compile_current(intent_object, evidence_object)
verification = verify_current(intent_object, evidence_object, receipt)
```

```bash
python -m tools.outbound_send_guard compile --intent intent.json --evidence evidence.json --out receipt.json
python -m tools.outbound_send_guard verify --intent intent.json --evidence evidence.json --receipt receipt.json --out verification.json
```

Package-level `evaluate` is `compile_current`. Compatibility `tools.outbound_send_guard.guard.evaluate(...)` is also verifier-clock current, and the old `python -m tools.outbound_send_guard.guard ...` syntax routes through the same current compiler.

The deterministic v1 engine is preserved byte-for-byte as underscore-private `_guard_core.py` for reconstruction, focused engine tests, and internal composition. The reviewed verifier-clock implementation from the original #14333 carrier is preserved byte-for-byte as `current_impl.py`. `current.py` is a small safety wrapper that binds `current_impl` to the private core without exporting that core through `current.guard`.

`guard_legacy.py` is now an explicitly historical, non-authorizing compatibility surface. Historical evaluation requires an explicit timestamp and emits only `HISTORICAL_INTEGRITY_ONLY` with outward `HOLD`; its CLI always returns HOLD. No supported compatibility API returns the old positive receipt as current authority.

## Current decisions and authority

The current receipt preserves the deterministic core decision while binding verifier-owned time and expiry:

- `ALLOW_NEW` — complete evidence is fresh at verifier time and no exact-offer/cooldown/DNR blocker exists;
- `REPLY_ONLY` — a recipient inbound is newer than the latest outbound;
- `HOLD` — evidence is incomplete, stale, future-dated, contradictory, expired, or another outbound is inside cooldown;
- `DO_NOT_RESEND` — a hard DNR or exact-offer outbound exists.

Every compiler and verifier result sets `side_effects_authorized=false`. A current positive result is only a prerequisite. Muse election/custody, relationship and route controls, provider reread, one-shot send consumption, and the actual provider mutation remain separate boundaries.

Current authority uses code-owned ceilings: evidence age 900 seconds, request age 900 seconds, future skew 300 seconds, and positive receipt lifetime 60 seconds. Candidate policy may tighten but never widen them. Current verification replays the receipt at its bound verifier time and then reassesses it under fresh process UTC; expiry, source change, reseal, or semantic drift fails current preflight.

## Source custody

Parsed-object APIs canonicalize and detach one object generation before evaluation. Exact-byte APIs hash the same bytes they strict-parse. Inputs reject duplicate JSON keys, non-finite values, coercive booleans/integers, unknown fields, naive timestamps, malformed addresses, oversized evidence, and conflicting duplicate provider/Slack identifiers.

The CLI consumes bounded no-follow regular files and creates outputs exclusively. Existing output paths and final-component symlinks are refused.

## Regression gate

The dedicated workflow runs Python 3.11 and 3.13 in normal and optimized (`-O`) modes over:

- the full deterministic v1 engine test suite against `_guard_core`;
- current verifier-clock semantics and expiry/custody hostiles;
- compatibility `guard.evaluate` stale-pair replay closure;
- package/guard CLI convergence;
- explicit historical HOLD-only behavior;
- absence of caller-clock current authority parameters.

The predecessor exploit is pinned directly: matched 2025 intent/evidence may still reconstruct a historical core `ALLOW_NEW`, but both package `evaluate` and compatibility `guard.evaluate` must emit current `HOLD` with `current_preflight_clear=false`.

See `CURRENT_TIME.md` for the exact authority boundary.
