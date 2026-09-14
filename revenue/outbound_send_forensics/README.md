# Outbound send pre-send forensics

This package audits **already-attempted external sends** against the connector-native
lease protocol in `revenue/outbound_connector_lease`. It exists for the failure
mode where a worker crosses Gmail/Slack/web-form first and creates the canonical
GitHub lease branch afterward. A late branch is useful as permanent DNR state,
but it is **not evidence that the send was mutex-protected**.

This is deliberately separate from the prospective send guard / one-shot
consumer. It performs no provider call, creates no Git ref, sends no message and
never turns a bad historical send into an authorized one.

## Claim ceiling

The verifier is structural and temporal. `PROTECTED_PRE_SEND` means the input
contains:

1. a canonical seam that recompiles through the landed v1 lease compiler;
2. a provider SENT evidence envelope marked `provider-receipt`;
3. an exact successful GitHub create-branch evidence envelope marked
   `github-create-result` for that seam; and
4. a lease-create timestamp strictly earlier than the provider SENT timestamp.

The JSON labels do not magically prove an external receipt exists. Operators
must retain the actual provider/GitHub receipts whose SHA-256 digests are bound
into the record. Caller prose or branch existence alone must use
`caller-assertion` / a non-`created` result and will classify
`AMBIGUOUS_UNTRUSTED_EVIDENCE`.

Every audited send is `dnr: true`, including ambiguous evidence. A historical
violation is a reason to reconcile and suppress retries, not permission to send
again.

## Input contract

Top level is an exact-field document:

```json
{
  "schema": "outbound-send-forensics/v1",
  "records": [
    {
      "record_id": "sd-doh-27-09rht-025-1",
      "seam": {
        "schema": "outbound-connector-lease/v1",
        "buyer_scope": "sd.gov",
        "opportunity": {
          "kind": "external",
          "authority": "sd.gov",
          "id": "27-09rht-025"
        }
      },
      "send": {
        "provider": "gmail",
        "event_id": "provider-message-id",
        "sent_at": "2026-09-14T01:14:12Z",
        "authority": "provider-receipt",
        "status": "sent",
        "receipt_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
      },
      "lease_create": {
        "branch": "outbound-connector-lease/v1/<64 lowercase hex>",
        "created_at": "2026-09-14T01:15:34Z",
        "authority": "github-create-result",
        "result": "created",
        "base_sha": "<40 lowercase hex commit>",
        "receipt_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
      }
    }
  ]
}
```

`lease_create` may be `null` when no lease evidence exists. Evidence enums are
closed. Send provider IDs reuse the canonical v1 provider registry. Timestamps
must be strict RFC3339 with `T`, seconds and an explicit timezone. Hashes are
exact lowercase hex. Extra fields, duplicate JSON keys, non-finite values,
malformed branches, unsupported providers/results, naive timestamps and
contradictory duplicate provider events fail closed.

## Classifications

- `PROTECTED_PRE_SEND` — exact authoritative lease-create evidence matches the
  recompiled seam and is strictly earlier than provider SENT.
- `POST_SEND_LEASE_VIOLATION` — matching successful lease create is simultaneous
  with or later than provider SENT. Equal timestamps are not treated as proof of
  ordering.
- `MISSING_LEASE` — provider SENT evidence exists but no lease-create evidence
  was supplied.
- `SEAM_MISMATCH` — an authoritative successful create exists, but for a
  different canonical branch.
- `AMBIGUOUS_UNTRUSTED_EVIDENCE` — provider send is ambiguous/caller-asserted,
  or lease evidence is caller-asserted / exists / failed / ambiguous instead of
  the exact successful create result.

A batch also groups distinct provider event IDs by canonical seam. More than one
send event on one seam adds `DUPLICATE_SEND_SAME_SEAM` to every affected receipt
and emits an `incident_seams` entry. The batch result is input-order independent.
Exact duplicate provider events are rejected; conflicting copies are rejected as
contradictory evidence rather than guessed through.

## Deterministic receipts

Each normalized receipt gets `receipt_sha256`; the batch gets `batch_sha256`.
Inputs are normalized to UTC and receipts are sorted by normalized `record_id`.
The digests cover the canonical JSON payload excluding only the digest field
itself. They bind what this verifier concluded; they do not elevate caller JSON
into provider authority.

## Run

```bash
python -m revenue.outbound_send_forensics.audit evidence.json --pretty
```

or pipe JSON on stdin:

```bash
cat evidence.json | python -m revenue.outbound_send_forensics.audit -
```

Exit `0` means the evidence document was structurally auditable. Incident
classifications still appear in the output and do **not** change to success just
because the CLI exited cleanly. Invalid / unauditable input exits `2` with a
`HOLD:` diagnostic.

## Validation

```bash
python -m py_compile \
  revenue/outbound_send_forensics/audit.py \
  revenue/outbound_send_forensics/test_audit.py
python -m unittest -v revenue.outbound_send_forensics.test_audit
python -O -m unittest -v revenue.outbound_send_forensics.test_audit
```

The hostile suite covers pre/post/equal ordering, missing and wrong seams,
branch-existence non-proof, caller assertions, ambiguous sends, timezone
normalization, strict RFC3339, malformed hashes/branches, exact-field failures,
duplicate JSON keys, non-finite JSON, duplicate IDs/events, contradictory event
copies, same-seam duplicate sends, compiler normalization and deterministic
receipt ordering/hashes.
