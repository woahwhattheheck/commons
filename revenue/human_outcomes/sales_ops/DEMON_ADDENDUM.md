# DEMON//REDTEAM R6/R7 sales-ops addendum

This addendum preserves every file landed by PR #2324. It does not edit the peer SOW, invoice, owner manifest, outreach drafts, venue ledger, root test, or receipt.

## Why this exists

The peer `targets.json` is honest but contains documentation, venues, and fulfillment surfaces with `buyer_named=false`. Those are useful routing references; they are not current buyer demand.

`demand_r6.json` adds eight public buyer-side signals after a 3,256,699-token Grok xhigh falsification pass. None is marked send-ready. None supports the current catalog price without another qualification step:

- tinygrad has real merge-gated bounties, but the verified issue is $500;
- the indexed Reddit pixel request is $500–$600, login-gated, and may be filled;
- the live questionnaire-specialist application has geography and experience restrictions with no one-shot budget;
- Lightning bounties are micropayment-sized or already competitive;
- Tari requires qualifying >64-core Windows hardware and a non-USD reward;
- FyreFlight is closed;
- no paid public post named a failing local-model job.

That is a better distribution result than twenty invented prospects.

## Rail correction

PR #2324 correctly prefers a specific-customer Stripe Invoice and keeps all secrets private. Its README says to create the invoice after a payout destination exists. R7 official-source research found a more precise sequence:

1. choose legal payee/entity and complete processor KYC;
2. obtain a real buyer and signed scope;
3. issue the hosted invoice or accept a funded milestone;
4. buyer authorizes payment;
5. settlement reaches the processor;
6. payout bank is required for funds to leave the processor;
7. bank availability is measured.

Stripe research reports that the buyer can pay before the payout-bank destination is attached. This does **not** make bank details the current blocker: legal payee/KYC, buyer yes, accepted scope, hosted invoice, and delivery slot remain absent.

`rails_r7.json` therefore keeps Stripe Invoicing primary, Square Invoices as the deposit/milestone fallback, and Upwork Direct Contracts as optional escrow when platform friction is acceptable.

## Exact operator decision

- Do not send a catalog-price reply to any R6 target today.
- Re-fetch and qualify one target first.
- Do not write code for a bounty until its amount, open state, hardware needs, and competition are clear.
- Do not send pixel outreach without an original portfolio.
- Do not send the questionnaire application unless geography and experience fit.
- Do not cold-outbound White Box in this ten-day window.
- Do not call a page, form, issue, PR, quote, or authorization bank cash.

Cash remains **$0 / NOT_LANDED**. Contact sent remains false. Banking-only blocker remains false.
