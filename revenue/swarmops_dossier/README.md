# Commons SwarmOps Evidence Dossier

SwarmOps turns owner-curated Commons evidence into a prospect-safe dossier without collapsing repository activity, queued CI, outbound transport, buyer acceptance, payment, or recognized revenue into the same claim.

## Current readiness vs historical replay

Output schema v4 makes the evaluation mode explicit.

- `CURRENT_PROCESS_UTC` means the evaluation instant came from the running process, not the packet or CLI caller.
- `HISTORICAL_INTEGRITY_ONLY` means a caller supplied an explicit replay time through the named library/test boundary. Its top-level `status` is always `NON_CURRENT`. The engine preserves the replay result separately as `historical_status`, but that value is never current authority.

Normal public CLI compile/verify does **not** take a currentness timestamp:

```bash
python -m revenue.swarmops_dossier.cli compile packet.json policy.json \
  --json-out dossier.json --markdown-out dossier.md
python -m revenue.swarmops_dossier.cli verify packet.json policy.json dossier.json
```

The exported current library functions capture their stdlib UTC clock generation when `current.py` initializes. They do not perform a later module-name lookup for the clock. The clock factory/name is deleted after construction, and reload purges the predecessor `_process_utc_now_text` seam. Ordinary module/global reassignment therefore cannot replace the current clock or freeze verification at a historical instant. This is an in-process authority boundary against normal rebinding/monkeypatching, not a claim to survive arbitrary interpreter memory/code takeover.

The current verifier first authenticates the candidate at its recorded process-owned `as_of`, then samples the sealed process UTC clock again and recompiles the packet. Verification succeeds only while the semantic readiness projection is still identical. A once-ready receipt therefore stops verifying as current when required evidence becomes stale, moves into the future relative to the verifier, or otherwise changes classification/status.

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

Library callers use `compile_current_dossier()` / `verify_current_dossier()` for current semantics and `compile_historical_dossier()` / `verify_historical_dossier()` for deterministic replay.

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

## Verification

The v4 receipt binds the complete wrapped dossier, including evaluation mode and the underlying v3 semantic receipt. Current verification:

1. rejects non-v4 or non-`CURRENT_PROCESS_UTC` candidates;
2. rejects a candidate evaluated in the verifier's future;
3. recompiles at the candidate's recorded time and requires exact receipt equality;
4. samples the sealed process UTC clock and recompiles again;
5. compares the complete semantic projection while excluding only evaluation/receipt-time fields.

Historical verification is exact deterministic replay and never upgrades the artifact to current.

Focused commands:

```bash
python -m revenue.swarmops_dossier.acceptance
python -m unittest revenue.swarmops_dossier.test_engine
python -m unittest revenue.swarmops_dossier.test_current
python -O -m unittest revenue.swarmops_dossier.test_engine
python -O -m unittest revenue.swarmops_dossier.test_current
```

The normal `test_current` suite also launches a real `python -O` child replay. Its predecessor killers cover ordinary legacy-clock module reassignment before compile/verify and a normal `importlib.reload()` after a fake legacy clock is inserted; neither may mint caller-time `CURRENT_PROCESS_UTC` nor keep a historically READY receipt current after real expiry.

## Authority ceiling

Offline owner-review evidence only. This package does **not** authorize email/Slack/customer contact, provider/account access, credentials, deployment, proposals/submissions, pricing/staffing/legal/compliance commitments, signatures/contracts, spend, payment actions, buyer-acceptance claims, cash assertions, or revenue recognition.
