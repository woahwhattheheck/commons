# Outbound send pre-send forensics

This package audits **already-attempted external sends** against the connector-native
lease protocol in `revenue/outbound_connector_lease`. It is offline: it performs no
provider call, creates no Git ref, sends no message, and never turns a historical
violation into permission to retry.

## Authority / claim ceiling

`PROTECTED_PRE_SEND` requires all of the following evidence:

1. a seam that recompiles through the landed v1 lease compiler;
2. provider SENT evidence marked `provider-receipt`;
3. an exact successful create-branch result marked `github-create-result`;
4. that create result identifies repository **`woahwhattheheck/commons`** and the
   exact compiled seam branch; and
5. the lease-create timestamp is strictly earlier than provider SENT.

Repository identity is part of the normalized, sealed receipt. A genuine create of
the same branch name in a fork or any other repository is not the shared Commons
mutex and therefore classifies `AMBIGUOUS_UNTRUSTED_EVIDENCE` with `dnr: true`.

The JSON labels do not themselves prove external receipts exist. Operators must
retain the actual provider/GitHub receipts whose SHA-256 digests are bound into the
record. `repository_full_name` must come from that retained create result. Caller
prose, another-repo branches, or branch existence alone are not mutex authority.

## Evidence schema and compatibility

New evidence uses top-level schema `outbound-send-forensics/v2`. Legacy `outbound-send-forensics/v1` remains readable for historical audits, but its lease object had no repository identity; therefore a v1 record can never classify `PROTECTED_PRE_SEND` and is emitted as `AMBIGUOUS_UNTRUSTED_EVIDENCE`/DNR rather than guessed forward. Receipts/batches emitted by this verifier are v2.

For v2, `lease_create` is `null` or an exact-field object:

```json
{
  "repository_full_name": "woahwhattheheck/commons",
  "branch": "outbound-connector-lease/v1/<64 lowercase hex>",
  "created_at": "2026-09-14T01:15:34Z",
  "authority": "github-create-result",
  "result": "created",
  "base_sha": "<40 lowercase hex commit>",
  "receipt_sha256": "<64 lowercase hex>"
}
```

Repository identity is normalized case-insensitively as `owner/repo`, but only
`woahwhattheheck/commons` can support positive pre-send protection. Malformed repo
IDs, extra fields, duplicate JSON keys, non-finite values, malformed branches or
hashes, unsupported providers/results, naive/non-RFC3339 timestamps, and
contradictory duplicate provider events fail closed.

## Classifications

- `PROTECTED_PRE_SEND`: canonical-repository create matches the seam and predates SENT.
- `POST_SEND_LEASE_VIOLATION`: matching canonical-repository create is equal/later.
- `MISSING_LEASE`: provider SENT exists without lease-create evidence.
- `SEAM_MISMATCH`: canonical-repository create proves a different branch.
- `AMBIGUOUS_UNTRUSTED_EVIDENCE`: caller/ambiguous/non-create evidence **or a create
  result from a noncanonical repository/fork**.

Every audited send remains DNR. Distinct provider event IDs on one seam add
`DUPLICATE_SEND_SAME_SEAM`; duplicate/conflicting copies of one provider event fail.

## Deterministic receipts

Per-record v2 receipts include `source_input_schema`, `expected_lease_repository`, and
`lease_repository_full_name`; all are covered by `receipt_sha256`. Batch output is
input-order independent and sealed with `batch_sha256`. These digests bind what the
verifier concluded; they do not elevate caller JSON into provider authority.

## Run / validation

```bash
python -m revenue.outbound_send_forensics.audit evidence.json --pretty
python -m py_compile revenue/outbound_send_forensics/audit.py revenue/outbound_send_forensics/test_audit.py
python -m unittest -v revenue.outbound_send_forensics.test_audit
python -O -m unittest -v revenue.outbound_send_forensics.test_audit
```

Exit `0` means structurally auditable, not "safe to send". Invalid input exits `2`
with `HOLD:`. The hostile suite covers chronology, canonical-vs-fork repository
identity, malformed repo IDs, caller assertions, branch existence/non-create,
provider registry, strict JSON/time/hash/type boundaries, duplicate send incidents,
seam normalization, and deterministic receipts.
