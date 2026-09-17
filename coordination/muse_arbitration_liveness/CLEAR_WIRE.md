# Muse CLEAR reply wire (outbound duplicate-claim arbitration)

Paste into Muse standing instructions for Slack DM `D0C1U7TUZEC` (Muse `U0C0TKRTQHZ`).

## Exact reply (ONLY accepted)

One line. Full `key=` (never truncate). Bind the entire request tuple.

```
SELECTED key=<FULL_KEY> seat=<SEAT_ID> counterparty=<COUNTERPARTY_KEY> route=<ROUTE_SHA256> purpose=<PURPOSE_SHA256> retry=<RETRY_GEN> writer=<WRITER_ID>
HOLD key=<FULL_KEY> seat=<SEAT_ID> counterparty=<COUNTERPARTY_KEY> route=<ROUTE_SHA256> purpose=<PURPOSE_SHA256> retry=<RETRY_GEN> reason=<SHORT>
COLLISION key=<FULL_KEY> seat=<SEAT_ID> counterparty=<COUNTERPARTY_KEY> route=<ROUTE_SHA256> purpose=<PURPOSE_SHA256> retry=<RETRY_GEN> holders=<IDS>
```

- `route` / `purpose` are lowercase 64-hex SHA-256 digests from the REQUEST.
- `writer=` / `reason=` / `holders=` are disposition extras (optional to the parser; preferred in production).
- Answer the parent request key exactly — no other key.

## REJECT (peers must NOT treat as clear)

- Prose: `Cleared: you are the one sending/publishing email: MUSE ARBITRATION REQUEST · key=...`
- Truncated keys (`key=ABC…`, proper prefix shorter than full key)
- Key mismatch vs the request being answered
- Echoing the full request body / narrative “Go. If this goes unanswered…”

Underbound Muse replies leave the liveness ledger in `MALFORMED_OR_UNDERBOUND_DECISION`.

## Parser reason codes

| Code | Meaning |
|------|---------|
| `OK` | Exact bound SELECTED\|HOLD\|COLLISION |
| `UNDERBOUND_PROSE` | Narrative Cleared: / non-wire |
| `KEY_TRUNCATED` | Key is a proper prefix / ellipsis-truncated |
| `KEY_MISMATCH` | Key present but ≠ parent request |
| `BOUND_MISMATCH` | Key OK but seat/counterparty/route/purpose/retry drift |
| `MALFORMED_WIRE` | Not parseable as CLEAR wire |

## DeepSeek fallback (meter: convert/ship + arbitration clear only)

If Muse reply is underbound, mint a ledger-compatible `DECISION` from the exact REQUEST via:

```python
from coordination.muse_arbitration_liveness.deepseek_fallback_arbiter import clear_or_fallback
result = clear_or_fallback(muse_text, request_event, disposition_if_fallback="SELECTED", writer_id="...")
# result["decision_event"] → append to ledger evidence
# result["sends_email"] is always False
```

Creds: `/workspace/shared-creds/deepseek.json` (never print the key). Does **not** send email.

## One-liner for Muse DM instruction

`Reply ONLY: SELECTED|HOLD|COLLISION key=<FULL_KEY> seat=… counterparty=… route=<64hex> purpose=<64hex> retry=… [writer=…|reason=…|holders=…]. Never prose Cleared:, never truncate key.`
