# Accepted scope to delivery

Commons already has offers, quotes, binary acceptance, DIO receipts, and
separated money states. Those modules do not, by themselves, turn a **real
buyer agreement** into the packet a founder can execute and a buyer can read.

This road does that composition. It does not invent the sale.

## What it produces

Given a written agreement (and optional observations / payment observations):

| Artifact | Locked only if |
| --- | --- |
| Statement of work | `LOCKED_SOW` requires `ACCEPTED` written terms |
| Work packet | Issued only from `LOCKED_SOW` |
| Execution status | Projected from observations; never from hope |
| Evidence bundle | Only `public_ref` + `sha256` rows |
| Delivery receipt | `delivered` only when every acceptance row is `PASS` |
| Invoice state | `ISSUED` only with an opaque processor ref |
| Payment state | `cash_claimed` only at `BANK_AVAILABLE` |
| Buyer handoff | Markdown + JSON, gaps listed, no testimonial field |

## Agreement states

`WRITTEN_INTAKE` → `TERMS_SENT` → `ACCEPTED` | `REJECTED` | `EXPIRED`

`ACCEPTED` is a measurement, not a mood. It requires:

- `written_acceptance.status = PRESENT`
- attestation `AUTHORIZED_OPERATOR_VERIFIED_EXACT_TERMS_ACCEPTANCE`
- `terms_digest` matching the canonical terms object
- a catalog SKU
- quote amount equal to the catalog total

## Execution states

`NOT_STARTED` | `RUNNING` | `BLOCKED` | `SUBMITTED` | `PASS` | `MISS`

`PASS` requires a `WORK_STARTED` observation and every binary row `PASS` with
hashes. Claiming complete without hashes is `SUBMITTED`, never `PASS`.

## Money states stay separated

`QUOTED != CHARGEABLE != INVOICED != AUTHORIZATION != SETTLEMENT != PAYOUT != BANK_AVAILABLE`.

A confirmed authorization does not start a false delivery. A bank credit does
not flip `delivered`. Catalog funnel truth on current main is still
`accepted_scopes: 0`, `paid_deliveries: 0`, `collected_cash_usd: "0.00"`.
Synthetic fixtures in `revenue/scope_to_delivery/fixtures/` prove the machine;
they are not live buyers.

## Public door

- Human: `scope-to-delivery.html`
- Machine: `revenue/scope_to_delivery/`
- CLI: `python3 host/scope_to_delivery.py`
- Catalog: `revenue/outcome_commerce/catalog.json`
- Bindings: `revenue/scope_to_delivery/catalog_bindings.json`

No login. No secrets on public main. Buyer names, emails, and addresses are
never filled. Possessing the link is sufficient to read the composer and run
it against the public fixtures.
