# Outbound provider preflight v1

`tools/outbound_send_guard/provider_preflight_v1.py` is the provider-history fence that complements canonical Muse publication election v2.

Canonical Muse v2 decides which candidate may hold the single-writer coordination seat. It deliberately sets `requires_fresh_provider_preflight=true` and never grants external-send authority. This module fills that separate provider-history seam without creating another election protocol.

## Result contract

The strongest positive result is `CLEAR_FOR_MUSE_PREFLIGHT`. It means a **complete retained provider ledger** contains no matching DNR, no exact-intent prior send, no same-publication prior send, and no source/order contradiction. It means only that the candidate may proceed to the canonical Muse/current-authority flow.

It never means “send.” Every report hard-codes external-send, provider-mutation, payment, contract, submission, and revenue authority to `false`.

Fail-closed results:

- `HOLD_LEDGER_INCOMPLETE` — provider history is not claimed complete.
- `HOLD_AFTER_DNR` — buyer + recipient + route has a DNR/hard-negative receipt.
- `HOLD_EXACT_INTENT_ALREADY_SENT` — exact publication + candidate + intent already has a provider send receipt.
- `HOLD_PUBLICATION_ALREADY_SENT` — the same canonical publication key has a send receipt for another candidate/intent, preventing two contenders from contacting the same publication target.
- `HOLD_EVIDENCE_ORDERING` — request/evidence occurs after snapshot `as_of_utc`.
- `HOLD_SOURCE_CONFLICT` — the same candidate digest is rebound to different publication/intent/buyer/recipient/route/operation semantics.

## Canonical identifiers

The request carries identifiers already present in canonical Muse v2 preparation semantics:

- `publication_key`
- `candidate_sha256`
- `intent_sha256`
- `buyer_scope_sha256`
- `recipient_fingerprint`
- `route_kind`
- `operation_id`

The guard accepts those identifiers as provider-normalization inputs; it does not reimplement the Muse election.

## Provider evidence

A send receipt records provider, provider message ID, send timestamp, canonical publication/candidate/intent/buyer/recipient/route/operation bindings. An exact send hard-stops the intent. A send for the same publication key but a different candidate also hard-stops, which closes the duplicate-hot-lead race at the provider ledger level.

A DNR receipt binds buyer + recipient + route plus provider reference, observation timestamp, and reason code. DNR is evaluated before send receipts and therefore wins as the stronger stop.

`ledger_complete=true` is required for the clear result. The tool does not attempt to infer completeness.

## Determinism and integrity

Input JSON is strict: duplicate keys, floats, NaN/Infinity, unknown/missing fields, malformed hashes/timestamps, duplicate provider message IDs, duplicate DNR refs, duplicate source-observation hashes, unsupported providers/routes, and oversized collections are rejected.

Rows normalize into deterministic order. The report contains `sourceDigestSha256` over normalized source and `receiptSha256` over the report payload. Verification recompiles the exact source, so a resealed semantic edit is still rejected.

## CLI

```bash
python tools/outbound_send_guard/provider_preflight_v1.py compile snapshot.json report.json
python tools/outbound_send_guard/provider_preflight_v1.py verify snapshot.json report.json
```

Input is bounded UTF-8 from a regular file descriptor with final-component symlink refusal where `O_NOFOLLOW` exists. Output is create-exclusive `0600` and never overwrites an existing path.

## Fleet ordering

1. Normalize provider history and DNR evidence for the exact canonical publication candidate.
2. Run this guard.
3. Any HOLD stops the outbound lane until evidence is reconciled.
4. `CLEAR_FOR_MUSE_PREFLIGHT` permits only progression to canonical Muse election/current-authority checks.
5. Immediately before any real provider mutation, refresh provider evidence and rerun the preflight.
6. After a real send, retain the provider message ID as a send receipt so every later contender for the same publication fails closed.
