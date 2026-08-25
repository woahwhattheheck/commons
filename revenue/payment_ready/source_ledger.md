# Source ledger — payment-ready pack

Landing owner: `cursor-grok-46-payment-ready-20260825`  
Base main at write: `6aa069e7a92c63f862d7d009de3c721482e51832`

| Claim | Source | What it establishes |
|---|---|---|
| Mandate + $12k / 10d + $6k+$6k + AT1–AT6 + secrets-absent gate | Slack `1787645021.043069` taking `demon-redteam-payment-ready-20260825-02` | CARRIER_ONLY taking; do not remint |
| $12k-first after D0 plumbing; $500-first lost 3–1; demand UNKNOWN; cash=$0; no public binaries | Slack `1787644100.499729` cross-synthesis fallback | research, not collected cash |
| Consume portfolio; do not erase lanes | `revenue/portfolio_overdrive/portfolio.json` blob `471698d2` on later main | ten lanes; `collectable_usd=NOT_LANDED`; `banking_only_blocker=false` |
| Do not overwrite the $30k offer | `commercial.json` offer `white-box-gguf-pilot-30d` | PROPOSED; $15k+$15k; `payment_collection=NOT_PROVIDED_ON_THIS_PAGE` |
| Computer is not the product | `muhl/lda-docs/muhl_revenue_add_20260813/PRODUCT_LAW.md` | hide list; no factory sale |
| Keepable vs never-leave-the-room | `muhl/lda-docs/muhl_revenue_add_20260813/DELIVERABLE.md` | edited GGUF / notes vs titan/foundry |
| Acceptance is completion/rollback, not metric lift | `muhl/lda-docs/muhl_revenue_add_20260813/SOW_OUTLINE.md` §6 | change-order rule; customer inputs move the clock |
| $30k / $100k–$175k numbers | `FEE.md` + `commercial.json` | follow-on only after paid delivery |
| AUTH ≠ SETTLE ≠ BANK | `ground/CASH_NOW.md`, `ground/CASH_NOW.json` | public Stripe/PayPal clocks; bazaar USD=0 |
| Stripe settlement / first payout / same-day manual | https://docs.stripe.com/payouts measured 2026-08-25 | US T+2; first payout typically 7–14 days; same-day before 17:00 ET |
| Stripe invoices vs payment links | https://docs.stripe.com/invoicing | invoices are specific-customer; this leftover creates neither |
| Stripe KYC varies | https://docs.stripe.com/connect/identity-verification and https://support.stripe.com/questions/know-your-customer-obligations | jurisdiction UNMEASURED |
| PayPal withdrawal clocks | https://www.paypal.com/us/cshelp/article/how-do-i-get-money-out-of-my-paypal-account-help394 | Instant vs Standard 1–3d vs check 5–10d |
| W-9 exists; no tax facts invented | https://www.irs.gov/forms-pubs/about-form-w-9 | Request for TIN and Certification |
| DIO lifecycle stays | `revenue/dio/foundation.json` | JOB→QUOTE→ACCEPTED→DELIVERY; payment metadata ≠ delivery |
| Bazaar USD=0 | `bazaar.json` | collectable USD NOT_LANDED |
| Talk is not a land | `ground/LAND.md`, `ground/EXECUTE.md` | this leftover must be files on main |
| Open door / no auth | `ground/OPEN_DOOR.md` | no login on any lane |

Run/model receipt: Cursor Grok 4.6, Cursor Automation, landing owner
`cursor-grok-46-payment-ready-20260825`. No Claude verdict. No Direct
Grok Build. No titan write. No outreach. No bank data. No invoice
issued.
