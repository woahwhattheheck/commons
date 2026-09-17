# Commons SwarmOps Evidence Dossier

SwarmOps turns owner-curated Commons evidence into a prospect-safe dossier without collapsing repository activity, queued CI, outbound transport, buyer acceptance, payment, or recognized revenue into the same claim.

## Current semantic verification vs historical replay

Output schema v4 makes the evaluation mode explicit.

- `CURRENT_SEMANTIC_SNAPSHOT` means the candidate is eligible for **current semantic verification**. `compile_current_dossier()` samples the runtime UTC clock for its own snapshot, but the receipt does **not** attest that an arbitrary candidate's recorded `as_of` originated from that clock. `verify_current_dossier()` authenticates the candidate exactly and then re-evaluates the same evidence against a fresh verifier clock sample; success means the complete readiness semantics still match now.
- `HISTORICAL_INTEGRITY_ONLY` means a caller supplied an explicit replay time through the named library/test boundary. Its top-level `status` is always `NON_CURRENT`. The engine preserves the replay result separately as `historical_status`, but that value is never current authority.

Normal public CLI compile/verify does **not** take a currentness timestamp:

```bash
python -m revenue.swarmops_dossier.cli compile packet.json policy.json \
  --json-out dossier.json --markdown-out dossier.md
python -m revenue.swarmops_dossier.cli verify packet.json policy.json dossier.json
```

The exported current library functions capture one clock generation plus the compiler, canonical serializer, parser, wrapper, semantic projector, schema, and mode used for verification when `current.py` initializes. Rebinding those package-module names afterward cannot change the already-exported verifier generation. Candidate ingress is frozen only from exact built-in JSON containers/scalars before semantic access, so stateful `dict`/`list` subclasses cannot present one view during authentication and another during freshness comparison.

This is an in-process evidence boundary, **not same-process hostile-code attestation**. A caller that mutates the Python interpreter or dependency modules (including stdlib clock sources) before module initialization/reload is outside this contract. Direct replacement of the exported functions is likewise outside the boundary. The v4 mode is deliberately named `CURRENT_SEMANTIC_SNAPSHOT` rather than claiming unforgeable process-clock provenance.

Current verification ordering is fail-closed:

1. require exact plain-JSON candidate ingress plus schema/mode;
2. parse the candidate's recorded `as_of`;
3. exact-recompile the candidate at that instant and require byte-for-byte canonical receipt equality;
4. **only after candidate authentication completes**, sample the sealed verifier clock;
5. reject candidate times in that verifier's future;
6. recompile against the fresh verifier instant and compare the complete semantic projection, excluding only `as_of` and the two receipt hashes that necessarily vary with evaluation time.

A verification pause therefore cannot cross a freshness boundary while reusing a pre-authentication clock sample. A stale once-ready snapshot fails when required evidence changes classification/status. A recent caller-constructed snapshot may verify if it is byte-valid and its semantics are genuinely still current; that is intentional and does not assert timestamp provenance.

Caller-selected evaluation time is not part of the public CLI. Supplying legacy `--as-of` on a real command-line invocation is rejected. Deterministic replay is an explicitly named library/test boundary:

```python
from revenue.swarmops_dossier.current import (
    compile_historical_dossier,
    verify_historical_dossier,
)

replay = compile_historical_dossier(packet, policy, "2026-09-13T14:00:00Z")
assert replay["evaluation_mode"] == "HISTORICAL_INTEGRITY_ONLY"
assert replay["status"] == "NON_CURRENT"
assert verify_historical_dossier(
    packet, policy, "2026-09-13T14:00:00Z", replay
)
```

Historical artifacts are permanently `HISTORICAL_INTEGRITY_ONLY` / `NON_CURRENT` and cannot verify through the current boundary. A hidden argv-injection compatibility seam is retained only so pre-v4 programmatic tests can exercise historical parsing; it is not exposed by public CLI invocation and never yields current authority.

Library callers use `compile_current_dossier()` / `verify_current_dossier()` for current semantic verification and `compile_historical_dossier()` / `verify_historical_dossier()` for deterministic replay.

## Evidence semantics

Each input row binds one capability to a typed immutable source reference, SHA-256, observed state, observation time/freshness, release class, required flag, and bounded factual claim. The underlying v3 semantic engine classifies rows as `DEMONSTRATED`, `LIMITED`, `HELD`, or `UNKNOWN`; required capabilities need current prospect-safe technical evidence or the current dossier is `HOLD`.

Queued/running CI is not green. A provider send is not buyer acceptance. A merge is not payment. No state implies another.

## Commercial truth has a separate trust root

- `SENT_NOT_ACCEPTED` requires a provider-receipt row and never means acceptance.
- `BUYER_ACCEPTED` requires a buyer-receipt row plus independently retained exact buyer authority.
- `PAID` requires a payment-receipt row plus independently retained exact payment authority.
- `REVENUE_RECOGNIZED` requires an accounting-receipt row plus independently retained exact accounting authority.

The privileged engine/current APIs accept a host-owned authority map keyed by trusted `source_id`. Each authority record binds the exact portfolio and full commercial evidence semantics: capability, source kind/reference/SHA-256, commercial state, observation time/freshness, prospect release class, required flag, and claim. A digest match by itself is insufficient.

That prevents semantic transplantation: a retained payment receipt cannot be relabelled as buyer acceptance or accounting recognition, moved to another portfolio/capability/reference, refreshed in time, given a longer freshness window, or promoted from internal-only to prospect-safe. Malformed, inconsistent, or unused authority fails closed, and the authority generation digest is receipt-bound.

**A file supplied by the same CLI caller is not independent authority.** The public CLI exposes no commercial-trust option and always compiles/verifies with an empty trust map. A trusted host must acquire/authenticate buyer/payment/accounting evidence out of band and call the library boundary itself.

## Prospect and file boundaries

`INTERNAL_ONLY` evidence never appears in the prospect projection. `OWNER_APPROVAL_REQUIRED` cannot satisfy a required capability. Input JSON rejects duplicate keys and non-finite numbers. CLI inputs must be bounded regular files opened with no-follow and generation checks; outputs are mode-0600 create-exclusive files and are never overwritten.

## Verification and proof

Focused commands:

```bash
python -m revenue.swarmops_dossier.acceptance
python -m unittest -v revenue.swarmops_dossier.test_engine
python -m unittest -v revenue.swarmops_dossier.test_current revenue.swarmops_dossier.test_current_hardening
python -O -m unittest -v revenue.swarmops_dossier.test_engine
python -O -m unittest -v revenue.swarmops_dossier.test_current revenue.swarmops_dossier.test_current_hardening
```

`source-parses` is enrolled to run the SwarmOps currentness suites in normal and real optimized Python whenever this package changes. The retained hostile battery covers stale replay, future time, receipt tamper, module clock-name rebinding, reload cleanup, semantic-dependency rebinding, post-authentication clock ordering across a freshness boundary, exact plain-JSON ingress, historical/current separation, public CLI rejection of caller `--as-of`, and the explicit recent-snapshot truth-narrowing behavior.

## Authority ceiling

Offline owner-review evidence only. This package does **not** authorize email/Slack/customer contact, provider/account access, credentials, deployment, proposals/submissions, pricing/staffing/legal/compliance commitments, signatures/contracts, spend, payment actions, buyer-acceptance claims, cash assertions, or revenue recognition.
