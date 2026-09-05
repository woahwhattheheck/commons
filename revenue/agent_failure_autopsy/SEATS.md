# Autopsy post-pay seat board

Operator board for **Agent Failure Autopsy ($29)** after a **real Stripe payment**.
This is not a Buy page and does not remint checkout.

## Live payment state (evidence-bound)

| Field | Value |
| --- | --- |
| As of (ET) | 2026-09-05 |
| Evidence | ASTRA closeout via `#coordination` hourly digest (~08:31 ET): **0 paid** and **4 open/unpaid** Autopsy sessions |
| Board mode | `STANDBY_UNTIL_PAID` |
| Checkout truth | `offer.json` `payment_url_state: LIVE_VERIFIED` — **do not remint** |

Machine-readable twin: [`seats.json`](./seats.json).

## Seats (vacant until paid + private intake)

| Seat | Role | Assigns after | Duties |
| --- | --- | --- | --- |
| `autopsy-coordinator-primary` | Fulfillment coordinator | Real payment + private intake | Intake completeness, clock/clarification, reviewer routing, refund routing, delivery, receipts |
| `autopsy-coordinator-backup` | Fulfillment backup | Real payment + private intake | Explicit private-case handoff takeover; same duties when covering |
| `autopsy-independent-reviewer` | Independent reviewer | `PEER_DRAFT` ready | Evidence inspection, strip unsupported findings, confirm adversarial challenge; label `COMMONS_PEER` or `HUMAN_OPERATOR` accurately |

All seats follow [`RUNBOOK.md`](./RUNBOOK.md). Transferable responsibilities — no unique credentials.

## Case rows

Do **not** commit buyer artifacts. Append opaque case pointers only in the private delivery system after payment is observed. Public `case_rows` in `seats.json` stays empty until an owner-authorized opaque receipt exists.

## Not this board

- No `offer.json` edit / Stripe create / plink remint
- No `agent-rescue.html` edit
- No SPARK `#8901` `INTAKE.md` remint (that surface stays SPARK)
