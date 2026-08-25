# Secret-free stage evidence contract

`host/revenue_recovery.py` advances a recorded purchase intent through the
quote, acceptance, delivery, and processor-reference receipt stages. Previous
public receipts stay inside Commons; evidence manifests and private artifacts
must resolve from a separate root outside the Commons checkout. The instrument
writes nothing by default.

Never put a buyer identity, signature, contract text, model bytes, credentials,
bank, routing, card, tax, payout, or private provider payload in these files.
Store the private artifact on its proper owner-private surface. The instrument
reads the bytes and rejects a caller-supplied digest that does not match them.
Commons records only an opaque reference and the measured SHA-256; it never
emits a private local path.

Opaque references are labels, not filesystem locations. Drive prefixes,
absolute paths, backslashes, and slash-containing references are rejected for
both artifacts and processor events.

Every evidence file uses `schema_version: revenue-recovery-evidence/v1`.

## Quote

```json
{
  "schema_version": "revenue-recovery-evidence/v1",
  "stage": "QUOTE",
  "artifact": {
    "kind": "QUOTE_ARTIFACT",
    "reference": "owner-private:quote-opaque-id",
    "file": "quote.pdf",
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
    "file": "signed-acceptance.pdf",
    "sha256": "<64 lowercase hexadecimal characters>"
  }
}
```

The previous receipt must be an `OFFERED` quote. The resulting legal-acceptance
fact is explicitly `OWNER_REPORTED`, never inferred from public interest.

## Delivery

Use an `acceptance_tests` array ordered exactly AT1 through AT6. Each row has
`id`, `status: PASS`, a secret-free opaque `reference`, a relative private
`file`, and an exact measured `sha256`.
The previous receipt must be `ACCEPTED`. A missing, reordered, or non-PASS test
is rejected. The resulting delivery fact is `OWNER_REPORTED`.

## Processor reference

```json
{
  "schema_version": "revenue-recovery-evidence/v1",
  "stage": "PROCESSOR_REFERENCE",
  "provider": "Stripe",
  "opaque_reference": "stripe:event-opaque-id",
  "payload_file": "stripe-event.json",
  "payload_sha256": "<64 lowercase hexadecimal characters>"
}
```

The previous receipt must be `DELIVERED`. The provider must be `Stripe` or
`PayPal`. The result is only `REFERENCE_RECORDED`: processor payment, payout,
bank availability, and collected cash remain `NOT_LANDED` / USD 0.

## Command

```text
python3 host/revenue_recovery.py advance --stage QUOTE --previous-receipt path/to/previous.json --evidence-root /outside/commons/private-evidence --evidence-json quote.json
```

Replace `QUOTE` with `ACCEPTANCE`, `DELIVERY`, or `PROCESSOR_REFERENCE` as the
evidence chain advances. Save an emitted receipt only after reviewing it; the
instrument itself does not mutate Commons.

The evidence root must be disjoint from the Commons root: it may be neither
inside Commons nor an ancestor that contains Commons. Relative paths that
escape that root, missing bytes, and hash mismatches are rejected. `/owner-private/`
and `/.private-revenue-evidence/` are also ignored as a fail-safe, but they are
not valid evidence roots because private evidence must stay outside the checkout.
