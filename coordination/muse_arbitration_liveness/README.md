# Muse Arbitration Liveness Ledger

Offline/read-only coordination evidence for a single-writer outreach fleet.

The ledger answers a narrow question: **has an exact arbitration request been answered with an exact, sufficiently bound decision, and did the selected writer produce an exact provider send receipt?** It exists because an unanswered request can otherwise be mistaken for a lost lane, a truncated CLEAR can be mistaken for authority, and a stale selection can strand work or tempt another writer to race the same counterparty.

It does not replace Muse and it never authorizes a send, retry, reassignment, contact, provider mutation, acceptance, payment, or revenue claim. `as_of_utc` and retry/selection ages are caller-supplied audit policy; outputs are explicitly `HISTORICAL_EVIDENCE_ONLY`. `OWNER_REVIEW_RESUBMIT_DUE` and `OWNER_REVIEW_STALE_SELECTION` are review prompts, not authority.

## Input

Schema version 1 has `as_of_utc`, a policy with `resubmit_after_seconds` and `selection_stale_after_seconds`, and a flat `events` list.

A `REQUEST` binds one immutable tuple: `request_key`, `seat_id`, opaque `counterparty_key`, route digest, purpose/offer digest, and retry-policy generation. Exact retries repeat the same tuple under new provider event identities. Reusing a request key with changed tuple semantics is `CONFLICT`.

A `DECISION` records what the observed bot message actually binds. Binding fields may be `null` when a response is truncated/under-bound. Only an exact tuple match can become `SELECTED_AWAITING_SEND_RECEIPT`, `HOLD_OR_COLLISION`, or a stale-selection owner-review state.

A `SEND_RECEIPT` must exactly bind the selected request tuple and occur after an exact selection. Its presence yields `SENT_DNR`, which suppresses retry/reassignment suggestions in this ledger.

Provider event IDs are immutable evidence identities: same ID + changed digest is conflict. Exact replay collapses.

## CLI

```bash
python -m coordination.muse_arbitration_liveness.cli compile input.json packet.json
python -m coordination.muse_arbitration_liveness.cli verify input.json packet.json
```

Inputs use bounded nonblocking descriptor reads and must be ordinary regular files. Outputs are create-exclusive and refuse overwrite/symlink targets.

## States

- `PENDING_DECISION`
- `OWNER_REVIEW_RESUBMIT_DUE`
- `MALFORMED_OR_UNDERBOUND_DECISION`
- `HOLD_OR_COLLISION`
- `SELECTED_AWAITING_SEND_RECEIPT`
- `OWNER_REVIEW_STALE_SELECTION`
- `SENT_DNR`
- `CONFLICT`

All authority flags in compiled packets are literal `false`.
