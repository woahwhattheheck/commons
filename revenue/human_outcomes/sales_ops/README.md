# Human-outcomes sales ops — distribution / collection layer

Slack taking `1787649999.513539` / DEMON `demon-human-outcomes-sales-ops-20260825-01`.
Do not remint that id. Do not remint `demon-human-outcomes-revenue-20260825-01`.

This directory is the missing **distribution and collection** layer for
the four named human-outcome jobs already landed by PR #2312. It does
**not** replace the storefront. Hands off:

- `humans.html`
- `revenue/human_outcomes/offers.json`
- `revenue/human_outcomes/README.md`
- `revenue/human_outcomes/fulfillment.md`
- `host/human_outcomes.py`
- `ground/HUMAN_OUTCOMES.md`
- `test_human_outcomes.py`

Those blobs stay the catalog. This leftover adds private SOW/invoice
readiness, an owner-only field manifest, current public buyer-side
URLs, founder-reviewed outreach drafts, and a rail decision.

## Truth gate

Collected cash is **$0 / NOT_LANDED**. READY templates are not bank
cash. There is no checkout. No contact was sent. No private datum is
stored. No buyer is invented. Demand is UNKNOWN. No auth. No gate.

## Read first

| File | What it is |
|---|---|
| [owner_activation.json](./owner_activation.json) | Owner-only field manifest + rail decision. Surfaces, never values |
| [sow_template.md](./sow_template.md) | Private SOW blanks for all four SKUs. Unsigned. Not a contract |
| [invoice_template.md](./invoice_template.md) | Private invoice blanks. Fill only inside an official invoicing UI |
| [targets.json](./targets.json) | Current public buyer-side URLs measured 2026-08-25. Venues, not named buyers |
| [outreach.json](./outreach.json) | Founder-reviewed drafts. Status `NOT_SENT`. Contact sent: false |

Catalog numbers stay in `../offers.json`. Intake and founder-sent
contact stay in `../fulfillment.md`. Public door stays `../../humans.html`.

## Rail decision (one line)

Prefer a **Stripe Invoice for a specific customer** created inside the
official Dashboard after an owner-private payout destination exists.
Do not publish a Payment Link. Do not send an invoice from this
leftover. AUTH ≠ SETTLE ≠ PAYOUT ≠ BANK_AVAILABLE.

## Measure

```text
python3 -m unittest -v test_human_outcomes_sales_ops.py
python3 -m unittest -v test_human_outcomes.py
```

Hands off `revenue/dio/`, `commercial.json`, JOJO leftovers, CML 2108,
SPECTER 2205, titan `--go`, and `commons.mno`. titan: **NOT_WRITTEN**.
