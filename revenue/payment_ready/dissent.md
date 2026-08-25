# Dissent — banking is not the last blocker

Landing owner: `cursor-grok-46-payment-ready-20260825`

Premise under test: "once a routing/account number is connected,
first cash is unblocked."

**Verdict: false on current main.** Search space and failure modes
are named. A zero here is not stillness.

## Remaining blockers

1. **Buyer.** Cross-synthesis (`1787644100.499729`) kept demand
   UNKNOWN and conservative cash = $0. No public named buyer. No
   outreach from this leftover. Failure mode: treating an empty
   public buyer list as "buyers exist but are secret" *or* as "no
   buyers exist." Neither is measured. Gate: **NEEDS_BUYER**.

2. **Entity / payee.** `commercial.json` prints "Muhlnickel / Bryce
   Muhlnickel". That is a public provider string, not a measured
   legal-payee decision. D0 plumbing still lists legal payee as
   open. Failure mode: invoicing under an unchosen name. Gate:
   **NEEDS_OWNER_PRIVATE**.

3. **Tax.** IRS publishes Form W-9
   (https://www.irs.gov/forms-pubs/about-form-w-9). This pack does
   not determine whether a requester needs one, whether backup
   withholding applies, or whether sales tax is due. Inventing a
   rate would be a miss. Gate: **NEEDS_OWNER_PRIVATE**.

4. **Capacity.** Portfolio founder-slot rule: only one HIGH lane
   may be ACTIVE. White Box is the now-active HIGH lane. This 10-day
   diagnostic occupies that same slot as a precursor; it does not
   create a second founder day. Briefings, retainers, and expert
   networks stay blocked now. Failure mode: booking a diagnostic
   while a 30-day pilot is live.

5. **Trust.** NDA before file. Product law: computer is not the
   product. Public orig/ablated/restored binaries were rejected
   because a binary diff can leak method. A buyer who will not sign,
   or who demands a public dump, falsifies the offer.

6. **Delivery.** AT1–AT6 have never been run for a paying customer
   on the public record. Acceptance is rollback evidence, not metric
   lift. Failure mode: selling lift, or shipping without hashes.

7. **Rail, still open, but not sole.** Payout destination inside an
   official UI remains a real owner-private step (`CASH_NOW.md`).
   It does not erase 1–6. `banking_only_blocker` stays **false**.

## What would make banking the last blocker

Independent evidence of: a chosen legal payee, a signed NDA/SOW, a
buyer with a legally controlled GGUF and harness, founder calendar
clear, AT1–AT6 runnable privately, and tax/W-9 handled off-board.
Until then, a connected routing number would still leave collected
cash **$0 / NOT_LANDED**.

## What this dissent is not

It is not a claim that the $12k offer is unsupported. The synthesis
chose $12k-first over $500-first after plumbing (3–1). It is not a
claim that White Box $30k is collected. Rank is not BANK_AVAILABLE.
It is not outreach. It is not a Claude zero.
