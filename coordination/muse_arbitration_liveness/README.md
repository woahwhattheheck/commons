# Muse Arbitration Liveness Ledger

Offline/read-only coordination evidence for a single-writer outreach fleet.

The ledger answers a narrow question: **has an exact arbitration request been answered by the currently active, sufficiently bound decision, and did the selected writer produce an exact provider send receipt?** It exists because an unanswered request can otherwise be mistaken for a lost lane, a truncated CLEAR can be mistaken for authority, a stale selection can strand work, and a later explicit Muse correction can supersede an earlier erroneous decision.

It does not replace Muse and it never authorizes a send, retry, reassignment, contact, provider mutation, acceptance, payment, or revenue claim. `as_of_utc` and retry/selection ages are caller-supplied audit policy; all inputs are caller-supplied evidence and outputs are explicitly `HISTORICAL_EVIDENCE_ONLY`. `OWNER_REVIEW_RESUBMIT_DUE` and `OWNER_REVIEW_STALE_SELECTION` are review prompts, not authority. Action-time provider state remains authoritative.

## Input

Schema version 1 has `as_of_utc`, a policy with `resubmit_after_seconds` and `selection_stale_after_seconds`, and a flat `events` list.

A `REQUEST` binds one immutable tuple: `request_key`, `seat_id`, opaque `counterparty_key`, route digest, purpose/offer digest, and retry-policy generation. Exact retries repeat the same tuple under new provider event identities. Reusing a request key with changed tuple semantics is `CONFLICT`.

A `DECISION` records what the observed bot message actually binds. Binding fields may be `null` when a response is truncated/under-bound. A decision may additionally carry `supersedes_provider_event_id` (string or `null`) when the observed provider message explicitly corrects one earlier decision. Supersession is not inferred from recency: the target must exist, be a decision for the same request key, occur strictly earlier, and the superseding decision must bind the exact request tuple. Missing/wrong targets, same-time/backward targets, non-decision targets, self-supersession, multiple corrections of one target, or malformed chains fail closed as `CONFLICT`. Valid chains are allowed; only decisions not superseded by a valid later correction are active.

Only an active exact tuple match can become `SELECTED_AWAITING_SEND_RECEIPT`, `HOLD_OR_COLLISION`, or a stale-selection owner-review state. Unsuperseded contradictory exact decisions remain `CONFLICT`.

A `SEND_RECEIPT` must exactly bind the request tuple and occur after an **active** exact selection. A selection later superseded by HOLD/COLLISION cannot authorize a send; a correction that arrives after a send cannot retroactively authorize the earlier send. A valid receipt yields `SENT_DNR`, which suppresses retry/reassignment suggestions in this ledger.

Provider event IDs are immutable evidence identities: same ID + changed digest or changed parsed semantics is conflict. Exact replay collapses.

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

## CLEAR reply wire (Muse DM)

Outbound duplicate-claim CLEARs must use the exact `SELECTED|HOLD|COLLISION` wire documented in [`CLEAR_WIRE.md`](CLEAR_WIRE.md). Prose `Cleared:` replies are underbound and must not be treated as authority; peers may mint DeepSeek fallback DECISION evidence (meter: convert/ship + arbitration clear only; never send email) via `deepseek_fallback_arbiter.clear_or_fallback`.

