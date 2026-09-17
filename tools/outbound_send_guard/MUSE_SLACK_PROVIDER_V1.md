# Muse Slack provider evidence v1

`muse_slack_provider_v1.py` closes the caller-supplied-snapshot part of Commons #14503 without inventing send authority.

## What it proves

The adapter reads only four Slack Web API methods: `auth.test`, `conversations.info`, `conversations.history`, and `conversations.replies`. `auth.test` must identify workspace `T0BRETUB5TK`. `conversations.info` must identify direct-message conversation `D0C1U7TUZEC` whose peer is Muse user `U0C0TKRTQHZ`. History and thread replies are paginated to exhaustion over the canonical v2 collision window. Unsupported message subtypes, unattributable rows, malformed timestamps, cursor loops, incomplete pagination, and v2 message-bound overflow fail closed.

The exact request event in provider history determines the requester Slack user. No caller-supplied requester identity is accepted.

The returned provider receipt retains hashes of the canonical snapshot and provider binding. `verify_provider_evidence()` does not trust those hashes by themselves: while the 30-second receipt is fresh, it re-reads Slack at the retained capture boundary and requires byte-for-byte semantic reproduction of the full payload.

The Slack bearer token is read from `MUSE_SLACK_TOKEN`; it is used only as an Authorization header for the fixed read-method allowlist and is never serialized into a receipt.

## Requester control wire

After an exact canonical v2 request is posted, the provider-observed requester can suspend or retire that request with an exact control message:

```text
MUSE PUBLICATION CONTROL v1
action=HOLD
request_id=<canonical request id>
publication_key=<64 lowercase hex>
candidate_sha256=<64 lowercase hex>
```

Allowed actions are `HOLD`, `WITHDRAW`, `CANCEL`, and `RESUME`.

`HOLD`, `WITHDRAW`, and `CANCEL` force the provider observation to `HOLD` even if Muse later emitted an exact `SELECTED` line. `RESUME` never resurrects an older selection: a later exact Muse decision is required. Any other requester-authored follow-up that mentions the exact request id but does not match the strict control wire also forces `HOLD` as ambiguous. This avoids quoted/free-form negative-intent parsing while still failing closed on an unstructured same-request update.

## Deliberate authority ceiling

Provider authentication and retained receipt-ledger completeness are separate trust roots. This adapter does **not** accept a caller Boolean that says the prior receipt ledger is complete.

For diagnostic observation only, it asks the canonical v2 engine what the fetched Slack evidence would say if that independent ledger were complete. The canonical receipt from that counterfactual compile is never serialized. The provider receipt hard-codes:

- `prior_receipt_ledger_authenticated=false`
- `terminal_election_authorized=false`
- `external_send_authorized=false`
- `side_effects_authorized=false`
- `requires_current_worker_lease_possession=true`
- `requires_fresh_provider_preflight=true`

Therefore even `effective_observation=SELECTED` is coordination evidence, not permission to send. A future terminal-current adapter must add a separately reviewed provider-authenticated receipt ledger (or another equivalent replay-resistant authority source) and preserve the worker-lease/provider-preflight gates.

## Test contract

`test_muse_slack_provider_v1.py` uses a fake read-only Slack boundary and covers provider identity mismatch, DM-peer mismatch, thread inclusion, pagination exhaustion, provider-byte change on verification, strict requester controls, ambiguous requester follow-up, stale evidence, token non-disclosure, malformed/edited messages, and attempted authority-bit forgery.

Production code contains no Slack send/update/delete endpoint and no email, payment, invoice, contract, award, or revenue mutation surface.
