# Reconciliation portfolio registry

This directory turns provider-verifiable product receipts plus source-bound target research into a machine-checkable commercial portfolio. It intentionally separates **what is built** from **what might be sold** and **who may be contacted**.

## Files

- `catalog.json` — product receipts, commercial hypotheses, vertical bundles, intake/qualification/disqualification, objections, and authority ceilings.
- `targets/*.json` — five bundle-local files totaling 75 research-only account records (15 per bundle) with fit, first-party evidence, route state, and next action.
- `validate.py` — fail-closed semantic validator. It prevents non-merged products from becoming outreach-ready and forbids send authority in target data.
- `render.py` — deterministic buyer/ops-readable rendering of the exact JSON truth; generated output is intentionally not source-of-truth.
- `tests/test_recon_portfolio.py` — hostiles for truth promotion, target counts, provider-SENT DNR, product gates, and deterministic rendering.

## Truth model

`MERGED_DELIVERABLE` means a concrete provider PR is merged and a merge commit is recorded. It **does not** mean a buyer accepted, paid, saved money, or generated revenue. `OPEN_NEAR_SHIP` means the carrier is not merged or still has unresolved gates; the validator requires every target in such a bundle to remain `PRODUCT_GATE_HOLD`. `CONCEPT` is supported by the schema but cannot carry a merge SHA or become outreach-ready.

Every commercial figure is `PROPOSED_NOT_ACCEPTED`. The registry never creates contract, invoice, receivable, payment, savings, cash, or recognized-revenue truth.

## Route states

- `VERIFIED_CURRENT` — current first-party business route was evidenced during research. This is **not send permission**.
- `HOLD_ROUTE` — organizational fit exists but a clean buyer-appropriate route still needs research.
- `DNR_PROVIDER_SENT` — a selected provider send occurred; wait for a genuine inbound/provider event.
- `PRODUCT_GATE_HOLD` — source product is not currently sellable; do not qualify externally.

## Outbound mutex

No target row authorizes email, DM, form, phone, or any other contact. Before any future external touch, perform an exact organization + route + purpose Slack/Gmail census, obtain Muse single-writer selection, immediately recensus, and send at most once. Provider-SENT becomes hard DNR until a genuine human/provider event.

## Validate and render

```bash
python revenue/recon_portfolio/validate.py
python revenue/recon_portfolio/render.py --output /tmp/recon-portfolio.md
python -m unittest tests.test_recon_portfolio -v
python -O -m unittest tests.test_recon_portfolio -v
```

To render a human-readable view without creating another source of truth:

```bash
python revenue/recon_portfolio/render.py --output /tmp/recon-portfolio.md
```
