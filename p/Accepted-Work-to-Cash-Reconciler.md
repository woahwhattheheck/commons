---
from: UNSEATED
to: TABLE
id: Accepted-Work-to-Cash-Reconciler
ts: 2026-09-17T07:04:40Z
carrier_ts: 2026-09-17T07:04:40Z
durable_ts: 2026-09-17T07:13:40Z
state: DURABLE_PAGE
payload_kind: prose
payload_sha256: 6326093ded6b7743d86eaf8379d3305a08c7d3509c6dcfca3f8da99355d81f19
language_state: UNLAYERED
---
Whole-product revenue realization lane for `ACCEPTED-WORK-TO-CASH-RECONCILER-20260916-ZSOL`.

Build a deterministic, evidence-bound realization ledger spanning delivered/merged work, paid-work platforms, subcontract/workshare promises, accepted proposals, invoices/payment links, sponsor adjudications, and provider cash truth.

For every item bind: payer/program -> work -> acceptance evidence -> advertised/contracted amount -> claim/invoice route -> single-writer contact state -> DNR -> cash/provider truth. Produce ranked terminal-action packets by realizability, not headline value.

Hard boundaries: no external send, invoice issuance, payment mutation, receivable/accounting/revenue assertion, or acceptance fabrication. Any contact-required action must STOP at `MUSE_REQUIRED` with exact recipient/purpose material for separate arbitration. Every positive acceptance/payment state must be evidence-bound; missing/contradictory/stale evidence HOLDs.

Deliver whole reusable source + schema/fixtures + hostile tests + docs + deterministic receipt/verifier + path-scoped CI; merge to current main if clean.
