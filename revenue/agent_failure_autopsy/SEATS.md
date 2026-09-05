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
| `autopsy-coordinator-primary` | Fulfillment coordinator | Real payment + private intake | Intake completeness, clock/clarification, reviewer routing, refund routing, delivery, durable receipts (opaque `case_row` + optional G2 submit per RUNBOOK §10) |
| `autopsy-coordinator-backup` | Fulfillment backup | Real payment + private intake | Explicit private-case handoff takeover; same duties when covering |
| `autopsy-independent-reviewer` | Independent reviewer | `PEER_DRAFT` ready | Evidence inspection, strip unsupported findings, confirm adversarial challenge; label `COMMONS_PEER` or `HUMAN_OPERATOR` accurately |

All seats follow [`RUNBOOK.md`](./RUNBOOK.md). Transferable responsibilities — no unique credentials.

## Case rows (opaque receipt surface)

Do **not** commit buyer artifacts. Public `case_rows` in `seats.json` stays **empty** until an owner-authorized opaque receipt exists after `REAL_STRIPE_PAYMENT_OBSERVED`.

Checked-in shape (`case_row_shape` in `seats.json`):

- **Required:** `offer_id`, `case_ref`, `sku`, `state`
- **Optional:** `client_reference_id`, `g2_run_id`, `g2_session_id`, `payment_observed_at`
- **Builder:** `receipt_row_from_case(...)` in `integrations/grokbot_control/paid_case.py` (from a normalized G2 `case` + optional run/session ids)
- **Default state:** `UNVERIFIED`; the builder does not observe payment or sanitize values. Supply opaque identifiers and an evidence-supported state. Values over 200 characters raise instead of truncating.
- **Gate:** real Stripe payment observed + owner authorization — never invent a paid row to close a board

When a coordinator also opens Autopsy work on an existing GrokBot pool, attach `case` via `case_from_autopsy_offer` / `grokbot_submit` (RUNBOOK §10), then record the returned `run_id` / `session_id` on the opaque row.

## Not this board

- No `offer.json` edit / Stripe create / plink remint
- No `agent-rescue.html` edit
- No SPARK `#8901` `INTAKE.md` remint (that surface stays SPARK)
