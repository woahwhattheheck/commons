# Salesforce contact exactly-once preflight — receipt

Status: candidate implementation.

This public synthetic demo turns contact create/update/merge events into deterministic receipts before any live Salesforce work. It canonicalizes public match keys, rejects same-ID/different-bytes replay, preserves exact replay as a no-op, exposes field-level conflicts, and proves dashboard department totals reconcile to active canonical contacts.

## Trial

- Buyer: Salesforce operations owner and executive-reporting owner.
- Offer: $199, one business day, 20 supplied or synthetic events.
- Deliverables: canonical match-key map, automation trace, duplicate/conflict ledger, dashboard lineage totals.
- PASS: one active contact per unique person; replay is idempotent; conflicts are explicit; dashboard totals reconcile.
- Optional next step after PASS: $2,500 fixed-scope sandbox proof for one contact automation and one dashboard metric.

## Boundaries

No Salesforce credentials, production records, live-org writes, approval/denial, outreach, payment claim, or authentication/admission gate. This artifact makes no claim that Umoja accepted the offer or that the public page was delivered to the buyer.
