# Buyer Redline → Paid Scope Delta

Deterministic owner-review tooling for comparing a **structured, human-reviewed baseline offer/SOW** to a **structured counterdraft** without silently absorbing expanded work.

This is deliberately *not* a contract parser and not legal advice. It never signs, accepts, sends, changes a live price/payment rail, or recognizes revenue. Raw contract prose should first be extracted/reviewed by a human into the narrow JSON clause schema used here.

## Decisions

- `ACCEPTABLE_AS_WRITTEN` — structured clause facts are unchanged and exact baseline binding holds.
- `OWNER_REVIEW` — a material non-legal delta needs owner judgment.
- `REQUOTE_REQUIRED` — price/currency/payment timing or obvious cost/effort pressure changed.
- `LEGAL_REVIEW_REQUIRED` — IP, liability/warranty, or termination changed.
- `HOLD_CONTRADICTION` — source generation/binding or chronology conflicts; do not negotiate from this packet.

The counterdraft must name the exact `baseline_semantic_sha256`. Same-generation changed semantics and counterdraft chronology before the baseline fail closed.

## Clause schema

Each draft is JSON:

```json
{
  "schema": "buyer-redline-draft/v1",
  "document_id": "acme-pilot-sow",
  "generation_id": "g1",
  "observed_at": "2026-09-16T20:00:00Z",
  "clauses": [
    {
      "id": "commercial.price",
      "category": "price_payment",
      "metric": "fixed_price_minor",
      "statement": "Fixed fee in minor currency units",
      "value": 1250000
    }
  ]
}
```

A counterdraft has the same shape plus `baseline_semantic_sha256`.

Supported categories: scope, deliverables, acceptance, price/payment, schedule, data/security, IP, liability/warranty, termination, dependencies, assumptions.

## Hard gates

- duplicate JSON keys rejected;
- strict UTF-8, NFC strings, no surrogate text;
- floats/non-finite numbers rejected (money uses integer minor units);
- duplicate clause IDs and contradictory singleton commercial metrics rejected;
- raw and semantic SHA-256 identities retained;
- exact baseline semantic binding required;
- deterministic packet receipt independently verifies;
- all mutation/acceptance/legal/payment/revenue authority flags stay false.

## CLI

```bash
python -m revenue.buyer_redline_scope_delta.cli compile baseline.json counter.json packet.json --markdown owner.md
python -m revenue.buyer_redline_scope_delta.cli verify packet.json
```

Outputs are create-exclusive: the CLI refuses to overwrite an existing packet.
