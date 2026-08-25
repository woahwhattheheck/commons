# Secret-free stage evidence contract

`host/revenue_recovery.py` advances a recorded purchase intent through the
quote, acceptance, delivery, and processor-reference receipt stages. It reads
only files inside the Commons root and writes nothing by default.

Never put a buyer identity, signature, contract text, model bytes, credentials,
bank, routing, card, tax, payout, or private provider payload in these files.
Store the private artifact on its proper owner-private surface. Commons records
only an opaque reference and the SHA-256 of the exact private artifact.

Every evidence file uses `schema_version: revenue-recovery-evidence/v1`.

## Quote

```json
{
  "schema_version": "revenue-recovery-evidence/v1",
  "stage": "QUOTE",
  "artifact": {
    "kind": "QUOTE_ARTIFACT",
    "reference": "owner-private:quote-opaque-id",
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
  "artifact": {
    "kind": "SIGNED_ACCEPTANCE",
    "reference": "owner-private:acceptance-opaque-id",
    "sha256": "<64 lowercase hexadecimal characters>"
  }
}
```

The previous receipt must be an `OFFERED` quote. The resulting legal-acceptance
fact is explicitly `OWNER_REPORTED`, never inferred from public interest.

## Delivery

Use an `acceptance_tests` array ordered exactly AT1 through AT6. Each row has
`id`, `status: PASS`, a secret-free opaque `reference`, and an exact `sha256`.
The previous receipt must be `ACCEPTED`. A missing, reordered, or non-PASS test
is rejected. The resulting delivery fact is `OWNER_REPORTED`.

## Processor reference

```json
{
  "schema_version": "revenue-recovery-evidence/v1",
  "stage": "PROCESSOR_REFERENCE",
  "provider": "Stripe",
  "opaque_reference": "stripe:event-opaque-id",
  "payload_sha256": "<64 lowercase hexadecimal characters>"
}
```

The previous receipt must be `DELIVERED`. The provider must be `Stripe` or
`PayPal`. The result is only `REFERENCE_RECORDED`: processor payment, payout,
bank availability, and collected cash remain `NOT_LANDED` / USD 0.

## Command

```text
python3 host/revenue_recovery.py advance --stage QUOTE --previous-receipt path/to/previous.json --evidence-json path/to/evidence.json
```

Replace `QUOTE` with `ACCEPTANCE`, `DELIVERY`, or `PROCESSOR_REFERENCE` as the
evidence chain advances. Save an emitted receipt only after reviewing it; the
instrument itself does not mutate Commons.
