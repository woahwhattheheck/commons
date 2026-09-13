# Scope-to-delivery trusted-time gate

`host/scope_to_delivery.py` remains the canonical content composer for agreements,
work packets, execution evidence, delivery receipts, invoice state, and money
state. Its historical projection is deterministic, but the v1 schemas do not by
themselves establish that the agreement or observations are temporally current.

`host/scope_to_delivery_time_gate.py` is the mandatory temporal prerequisite
before treating a composed `LOCKED_SOW`, `ISSUED` work packet, or execution
observation as current work authority.

## Authority contract

The gate receives the exact agreement bytes, optional exact observation bytes,
and a trusted verifier clock. The library requires the clock out of band; the
CLI captures process UTC and exposes no caller-controlled `--as-of` override.

For `current_work_authorized=true`, all of the following must hold:

- the agreement is `commons-scope-agreement/v1` / `SCOPE_AGREEMENT`;
- `written_acceptance.status` is `PRESENT` and has a real `accepted_at`;
- acceptance is no later than the contracted window end and no later than the
  trusted verifier clock;
- the trusted verifier clock is inside the contracted work window;
- every execution observation is bound to the same agreement, is at or after
  acceptance, is inside the work window, and is no later than the trusted clock;
- duplicate observation identities, duplicate JSON keys, malformed timestamps,
  symlinked/non-regular input files, oversized inputs, and future evidence fail
  closed.

An expired window produces `HOLD_WINDOW_EXPIRED`. Historical observations that
were chronologically valid remain auditable, but an old `PRESENT` acceptance
cannot start new work after the window closes.

## Composition boundary

This gate proves chronology only. It does not replace the existing canonical
validation of catalog SKU, terms digest, quote amount/currency, buyer reference,
acceptance rows, evidence hashes, delivery, invoice, settlement, payout, or bank
availability. Consumers must require both the canonical composer validation and
a fresh temporal-gate result at the point current work would begin.

Every receipt therefore carries:

- `temporal_prerequisite_only=true`;
- `canonical_scope_validation_still_required=true`;
- `external_action_authorized=false`;
- `payment_authorized=false`;
- `delivery_claim_authorized=false`;
- `revenue_authorized=false`.

## CLI

```text
python3 host/scope_to_delivery_time_gate.py \
  --agreement revenue/scope_to_delivery/fixtures/accepted_agreement.json \
  --observations revenue/scope_to_delivery/fixtures/accepted_observations.json
```

Exit codes:

- `0`: temporal prerequisite is ready **at the verifier's current UTC instant**;
- `3`: truthful temporal HOLD (for example, window not started or expired);
- `2`: malformed, ambiguous, future, out-of-window, or unsafe evidence.

The public August 28 synthetic fixture is intentionally historical. On current
September 2026 execution it must return `HOLD_WINDOW_EXPIRED` / exit `3`, while
retaining `historical_evidence_temporally_admissible=true`.
