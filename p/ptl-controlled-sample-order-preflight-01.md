---
id: ptl-controlled-sample-order-preflight-01
title: PTL controlled-sample order preflight
agent: chatgpt-codex-root
demand: ptl-controlled-sample-order-preflight-01
buyer: Particle Technology Labs / Antonette R. Seneviratne-Anglewicz
gate: HOLD / BUILD-AND-VERIFY
cash_usd: 0
pre_sale_transport: NONE
---

# PTL controlled-sample order preflight

Shipped from the exact #delegations build demand at Slack timestamp
`1788233620.709999`.

## Product

A dependency-light CLI accepts normalized/redacted order packets, verifies LSO
and order ID, PO or approved-payment status, conditional SDS and DEA Form 222
presence flags, conditional international fields, requested turnaround, and
report-delivery route. It returns only
`READY_FOR_NAMED_HUMAN_ACCESSION` or fail-closed `HOLD` with a stable reason
code and deterministic SHA-256 evidence.

## Locked acceptance

| Metric | Value |
| --- | ---: |
| Synthetic/redacted packets | 12 |
| READY_FOR_NAMED_HUMAN_ACCESSION | 7 |
| HOLD | 5 |
| Each required HOLD reason | 1 |
| Real customer records | 0 |
| Autonomous accessions/releases/payments/transmissions | 0 |

HOLD codes: `MISSING_LSO`, `MISSING_PAYMENT_OR_PO`,
`MISSING_REQUIRED_SDS`, `MISSING_REQUIRED_DEA_222`, and
`INCOMPLETE_INTERNATIONAL_FIELDS`. Malformed or omitted condition inputs fail
closed as `MALFORMED_PACKET`.

## Commands

```bash
python3 revenue/ptl_controlled_sample_order_preflight/runner.py
python3 -m unittest test_ptl_controlled_sample_order_preflight.py
```

No LIMS accession/release, SDS/DEA/customs judgment, payment action, result
interpretation, external transmission, PTL contact, or production-readiness
claim. PRE-SALE TRANSPORT: NONE.
