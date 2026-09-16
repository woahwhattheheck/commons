# Secret-free stage evidence contract

`host/revenue_recovery.py` advances a recorded purchase intent through the
quote, acceptance, delivery, and processor-reference receipt stages. It reads
secret-free manifests inside Commons and exact private bytes beneath the
explicit external evidence root. It writes nothing by default.

Never put a buyer identity, signature, contract text, model bytes, credentials,
bank, routing, card, tax, payout, or private provider payload in these files.
Store the private artifact on its proper owner-private surface outside the
Commons checkout. Every `advance` run requires `--evidence-root` naming an
existing external directory. That directory must be disjoint from Commons: a
root equal to, inside, or containing the checkout is rejected. Symlinks and
relative traversal cannot escape it.

The secret-free manifest remains a repo-relative Commons file for deterministic
replay. Its POSIX-style `path` is resolved only beneath the external evidence
root. The instrument hashes those exact external bytes and rejects a claimed
SHA-256 that does not match. It emits only the opaque reference and verified
digest; it never emits the evidence root, local path, or bytes. Never place
private evidence beneath the checkout, even temporarily.

Every evidence file uses `schema_version: revenue-recovery-evidence/v1`.
The JSON Schema constrains receipt shape, stage/state/fact combinations, and
zero-cash claims. Runtime validation is the transition authority: it verifies
the exact source bytes, recursively replays every deterministic predecessor,
and requires the supplied receipt to equal that replay field-for-field.

## Quote

```json
{
  "schema_version": "revenue-recovery-evidence/v1",
  "stage": "QUOTE",
  "artifact": {
    "kind": "QUOTE_ARTIFACT",
    "reference": "owner-private:quote-opaque-id",
    "path": "quote.bin",
    "sha256": "<64 lowercase hexadecimal characters>"
  }
}
```

The previous receipt must be a `RECORDED` purchase intent. The resulting state
is `OFFERED`; it is not acceptance.

## Acceptance

```json
{
  "schema_version": "revenue-recovery-evidence/v1",
  "stage": "ACCEPTANCE",
  "nda": {
    "kind": "SIGNED_NDA",
    "reference": "owner-private:nda-opaque-id",
    "path": "nda.bin",
    "sha256": "<SHA-256 of exact NDA bytes>",
    "signed_at": "2026-08-25T14:00:00Z"
  },
  "sow": {
    "kind": "SIGNED_SOW",
    "reference": "owner-private:sow-opaque-id",
    "path": "sow.bin",
    "sha256": "<SHA-256 of exact SOW bytes>",
    "signed_at": "2026-08-25T14:01:00Z"
  },
  "m1": {
    "kind": "M1_PAYMENT_REFERENCE",
    "reference": "owner-private:m1-opaque-id",
    "path": "m1-reference.bin",
    "sha256": "<SHA-256 of exact M1 reference bytes>",
    "reference_at": "2026-08-25T14:02:00Z"
  }
}
```

The previous receipt must be an `OFFERED` quote. NDA, SOW, and M1 must have
three distinct references, paths, and digests. Their RFC3339 owner-reported
timestamp metadata is ordered strictly: both `signed_at` values must precede
the M1 `reference_at`. The receipt binds and orders that owner-reported
timestamp metadata; it does not independently prove legal signature or
payment chronology. Fractional seconds are preserved when each value is
normalized to UTC, so distinct ordered inputs cannot collapse to one displayed
second. Delivery can follow only the resulting acceptance
receipt. This represents the exact M1 term: `before customer file exchange;
after NDA and SOW signing`. M1 is a reference, not bank cash. The resulting
legal-acceptance fact is explicitly `OWNER_REPORTED`, never inferred from
public interest.

## Delivery

Use an `acceptance_tests` array ordered exactly AT1 through AT6. Each row has
`id`, `status: PASS`, a secret-free opaque `reference`, a temporary local
`path`, and the exact `sha256` of those bytes.
The previous receipt must be `ACCEPTED`. A missing, reordered, or non-PASS test
is rejected. The resulting delivery fact is `OWNER_REPORTED`.

## Processor reference

```json
{
  "schema_version": "revenue-recovery-evidence/v1",
  "stage": "PROCESSOR_REFERENCE",
  "provider": "Stripe",
  "opaque_reference": "stripe:event-opaque-id",
  "payload_path": "stripe-event.bin",
  "payload_sha256": "<64 lowercase hexadecimal characters>"
}
```

The previous receipt must be `DELIVERED`. The provider must be `Stripe` or
`PayPal`. The result is only `REFERENCE_RECORDED`: processor payment, payout,
bank availability, and collected cash remain `NOT_LANDED` / USD 0.
The receipt records the complete zero-cash lineage separately: processor
reference may be `REFERENCE_RECORDED`, while processor payment, payout, bank
availability, cash evidence, and collected cash remain `NOT_LANDED` / USD 0.
Its next step is `OWNER_PRIVATE_CASH_EVIDENCE`, not `BANK_AVAILABLE`; this
instrument has no automatic transition that can upgrade a processor reference
into cash.

Paths containing backslashes are rejected so a manifest resolves identically
on Linux and Windows. The external evidence root is mandatory for every later
stage and is propagated through recursive replay. Offer-source text hashing
intentionally canonicalizes LF and CRLF; evidence hashing intentionally does
not—artifact digests bind exact bytes. A valid-looking caller-built receipt is insufficient: the runtime
safe-resolves and hashes its source, validates each predecessor reference and
digest, recursively reconstructs the bounded stage chain, and exact-compares
the supplied receipt with the deterministic reconstruction.

## Command

```text
python3 host/revenue_recovery.py advance --evidence-root /absolute/private-evidence --stage QUOTE --previous-receipt path/to/previous.json --evidence-json path/to/evidence.json
```

Replace `QUOTE` with `ACCEPTANCE`, `DELIVERY`, or `PROCESSOR_REFERENCE` as the
evidence chain advances. Save an emitted receipt only after reviewing it; the
instrument itself does not mutate Commons.
