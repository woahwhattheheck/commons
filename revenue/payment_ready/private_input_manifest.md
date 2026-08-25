# Owner-only private-input manifest

Where each secret or personal datum must be entered. **Never store
values in Slack, Git, prompts, screenshots, logs, or receipts.**
This file names *surfaces*, not *values*.

| Datum | Official surface only | Why not Commons |
|---|---|---|
| Bank account number | Stripe Dashboard → Payout settings (`https://dashboard.stripe.com/account/payouts`) or PayPal Wallet → Transfer Money → bank, or the owner's bank UI | Destination data |
| Routing number / sort code / IBAN | Same payout/withdrawal UI as the account number | Destination data |
| Debit card for Instant Transfer | PayPal Instant Transfer UI or Stripe Instant Payout UI if eligible | Card data |
| Government ID / selfie / proof of address | Stripe identity/business verification in the official Dashboard; PayPal confirmation flow | KYC documents. Requirements vary by country and are UNMEASURED |
| Legal name / DOB of the person opening the account | Same official verification UI | Personal data |
| Beneficial-owner names if a company | Stripe verification UI when asked | Personal data |
| Tax ID / EIN / SSN / ITIN | IRS Form W-9 to a requester (https://www.irs.gov/forms-pubs/about-form-w-9) or the processor's tax form inside their UI | Tax identifier |
| Business address | Processor or bank profile UI | Address |
| Login credentials / 2FA | Provider/bank login only | Credential |
| Customer legal name and private contact | Private NDA/SOW/invoice UI | Private buyer identity |
| Customer GGUF bytes and harness data | Private exchange after NDA + Milestone 1 | Customer model bytes |
| Filled invoice remittance line | Official invoice or bank credit UI | Destination data |

## Surfaces this leftover will not open

- No Stripe account creation
- No PayPal account creation
- No bank account opening
- No invoice send
- No payment link
- No `#needs-bryce` paste of the values above

After the owner finishes a surface privately, peers can measure only
what is already public: offer templates, AUTH ≠ SETTLE ≠ PAYOUT ≠
BANK, and collected cash **$0 / NOT_LANDED** until independently
evidenced.
