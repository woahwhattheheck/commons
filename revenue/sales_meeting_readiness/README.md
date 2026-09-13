# Sales Meeting Readiness

`revenue.sales_meeting_readiness` is an offline control plane for the moment a commercial conversation is ready to become a meeting.

It enforces two operator rules mechanically:

1. **Never represent the owner as available until availability was independently checked against the exact requested window.**
2. **Never put the owner into a meeting without a concise preparation brief.**

The strongest output, `READY_FOR_OWNER_SCHEDULING_REVIEW`, is deliberately not scheduling authority. The package has no network client, no Google Calendar/Gmail/Slack adapter, and no ability to invite, reply, accept, reschedule, sign, quote, or spend.

## Evidence model

A packet contains opaque opportunity/thread identities, a retained inbound observation hash, requested windows, a preparation block, and optionally a separately retained calendar-availability observation. The availability observation must bind:

- the same opportunity and thread;
- IANA timezone and duration;
- a digest of the complete requested-window set;
- a digest of the retained busy-window set;
- a concrete proposed slot and a provider result (`FREE`, `BUSY`, or `UNKNOWN`).

The compiler recomputes both digests, checks freshness against verifier-owned current time, verifies the proposed slot fits a requested window with the exact duration, and recomputes overlap against half-open busy intervals. A claimed `FREE` that overlaps retained busy evidence is `HOLD`, not green. Exact boundary adjacency does not count as overlap.

## Preparation contract

A complete brief requires:

- sourced context facts;
- objective;
- key questions;
- likely asks;
- risks / commitments to avoid;
- recommended opening;
- recommended closing;
- owner actions.

Direct email addresses, phone numbers, common credential/token shapes, and raw private message text do not belong in the durable output. Source references should be opaque retained-evidence IDs.

## States

- `READY_FOR_OWNER_SCHEDULING_REVIEW` — current independent FREE evidence + exact slot + complete prep.
- `CALENDAR_CHECK_REQUIRED` — missing, stale, or unknown availability.
- `SLOT_CONFLICT` — retained busy evidence conflicts with the proposed slot.
- `PREP_REQUIRED` — calendar gate is clean, but one or more required brief sections are missing.
- `REQUEST_STALE` — the meeting request/slot has aged out.
- `HOLD` — structural, binding, integrity, chronology, or provider-evidence contradiction.

## CLI

Current compilation captures UTC internally; there is intentionally no production `--as-of` backdating flag.

```bash
python -m revenue.sales_meeting_readiness.cli compile \
  --input packet.json \
  --json-out readiness.json \
  --md-out meeting-brief.md

python -m revenue.sales_meeting_readiness.cli verify \
  --input packet.json \
  --receipt readiness.json
```

Outputs are create-exclusive. Existing files, symlink outputs, non-regular inputs, oversized inputs, duplicate JSON keys, unknown fields, unsafe types (`bool` as integer), non-canonical UTC, malformed hashes, and invalid timezones fail closed.

## Adapter boundary

A future Calendar adapter must obtain free/busy truth independently and then mint the availability observation. It must not accept caller-supplied `FREE` as authority. A future Gmail/Slack adapter may consume a verified owner decision, but this module must never be used as proof that a message was sent or a calendar event exists.

## Operator brief shape

The generated Markdown deliberately includes the context, objective, questions, likely asks, risks/commitments, recommended opening/closing, and owner actions needed to enter the call prepared.

## Test

```bash
python -m unittest revenue.sales_meeting_readiness.test_meeting_readiness -v
python -O -m unittest revenue.sales_meeting_readiness.test_meeting_readiness -v
python -m py_compile revenue/sales_meeting_readiness/*.py
```

The suite covers free/busy truth conflicts, exact boundary overlap semantics, missing/stale/future/transplanted availability, request binding, prep completeness, duplicate JSON keys, bool/int traps, timezone validation, PII/secret-shaped durable values, ordering invariance, receipt/policy tamper, create-exclusive outputs, symlink refusal, deterministic receipt/Markdown, and offline verification.
