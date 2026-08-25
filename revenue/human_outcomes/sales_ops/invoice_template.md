# Private invoice template — human outcomes

Fill these fields **inside an official invoicing UI**. Official
source measured 2026-08-25 HTTP 200:
https://docs.stripe.com/invoicing

Stripe invoices bill a **specific customer** and are not reusable
Payment Links (same page: Invoicing vs Payment Links). This leftover
creates neither. Collected cash is **$0 / NOT_LANDED**.

Never commit filled values. Never paste remittance, hosted invoice
URLs, tax IDs, addresses, or credentials onto Commons or Slack.

## Header (all blank on Commons)

| Field | What goes there | Public Commons |
|---|---|---|
| invoice_id | minted by the seller UI | leave blank |
| invoice_date | date of issue | leave blank |
| seller_legal_name | owner-private payee | leave blank |
| seller_contact | owner-private | leave blank |
| buyer_legal_name | owner-private | leave blank |
| buyer_email | official invoice customer record only | leave blank |
| currency | USD | USD |
| payment_terms | owner-private | `NOT_PROVIDED_ON_THIS_PAGE` |
| tax_line | owner-private determination | do not invent a rate or nexus |
| remittance | official provider invoice or owner-private bank UI | never paste here |

## Line items (amounts are public; names are not)

Pick the row that matches the signed private SOW. Do not list a
USD checkout on `humans.html`.

| Offer id | Description (public phrase) | M1 USD | M2 USD | Total USD |
|---|---|---|---|---|
| `ho-issue-to-pr` | Named issue to a CI-green PR, 7 calendar days | 1250 | 1250 | 2500 |
| `ho-meeting-packet` | Accessible public-meeting packet, 5 calendar days | 600 | 600 | 1200 |
| `ho-security-questionnaire` | Security questionnaire completion, 10 calendar days | 1500 | 1500 | 3000 |
| `ho-pixel-pack` | 8-bit / pixel agent pack, 5 calendar days | 400 | 400 | 800 |

M1 is due before work starts, after written intake. M2 is due only
on catalog acceptance. If acceptance never happens, the second half
is withheld. That is not a BANK_AVAILABLE event.

## Rail

Preferred: create the invoice inside
https://docs.stripe.com/invoicing/dashboard (HTTP 200 on 2026-08-25).
Backup: a PayPal request to a specific customer; withdrawal help at
https://www.paypal.com/us/cshelp/article/how-do-i-get-money-out-of-my-paypal-account-help394
(HTTP 200). Owner-private ACH/wire remittance stays inside a bank UI.

Do not send from this leftover. Authorization is not settlement is
not payout is not bank-available cash.
