# Buyer pack — $12k / 10-day GGUF diagnostic

Templates only. Not a signed contract. Not tax advice. Not a payment
link. `payment_collection=NOT_PROVIDED_ON_THIS_PAGE`. Collected cash
is **$0 / NOT_LANDED**. Do not paste bank, routing, card, tax-ID,
address, credential, or private-buyer data onto this page.

Canonical numbers live in [pack.json](./pack.json). The landed $30k /
30d White Box offer stays in `commercial.json` and is not replaced.

## 1. One-page scope

**Product:** White Box diagnostic on **their** GGUF.  
**Term:** 10 calendar days.  
**Fee:** USD 12,000 fixed. USD 6,000 before file exchange (after NDA
and SOW). USD 6,000 on AT1–AT6.  
**Buyer supplies:** a legally controlled GGUF, a runnable evaluation
harness with representative tests, one technical owner, and a private
exchange path.  
**Provider does:** one reversible ablation, byte-exact restore, harness
runs, concise finding, receipt.  
**Acceptance:** rollback evidence. Not metric lift.  
**Customer keeps:** original / ablated / restored artifacts exchanged
privately, hashes, harness logs, finding, receipt.  
**Provider keeps:** the computer, White Box machinery, targeting
methods, foundry, hide list.  
**Follow-on (separately scoped):** same-GGUF $30k / 30d pilot only
after AT1–AT6; $100k–$175k organization license only after paid
delivery (`commercial.json`, `FEE.md`).  
**Out of scope:** titan, foundry, allocator, live offsets, public
binary dump, production integration, extra model families, safety
certification.

## 2. Acceptance matrix (AT1–AT6)

| ID | Test | Pass | Fail |
|---|---|---|---|
| AT1 | original hash | SHA-256 of the supplied GGUF recorded before any edit | no pre-edit hash |
| AT2 | ablated hash different | ablated SHA-256 ≠ AT1 | hash unchanged or missing |
| AT3 | byte-exact restore | restored SHA-256 = AT1 | restore mismatches |
| AT4 | customer harness logs | baseline, ablation, and restore logs from **their** harness | provider-only numbers, or harness never ran |
| AT5 | concise finding | short written finding: shown / measured / limited | metric-lift claim used as acceptance |
| AT6 | receipt | artifacts + hashes named; payment reference is metadata only | receipt claims PAID proves delivery |

Falsifier: no NDA/SOW; no legally controlled file; harness never runs;
public orig/ablated/restored binaries; hide-list transfer.

## 3. Delivery checklist

1. NDA signed. SOW names the target and protected behaviors.
2. Milestone 1 recorded as authorized **off** Commons. File exchange
   only after that. Do not publish the file.
3. Record AT1. Perform one bounded ablation. Record AT2.
4. Restore. Record AT3. Run their harness. Keep AT4 logs private.
5. Write AT5. Issue AT6. Milestone 2 is due only if AT1–AT6 pass.
6. Inventory out: no titan, foundry, nring2, copier, allocator, live
   offsets, or reproduction method.
7. Optional next SOW: `white-box-gguf-pilot-30d`. Do not auto-start.

Delays in customer inputs move the 10-day clock by the same number of
days (`SOW_OUTLINE.md` customer-responsibilities rule).

## 4. Refund and change-order boundaries

These are working boundaries, not statutory rights and not legal
advice.

- **Metric non-lift is not a refund.** Acceptance is AT1–AT6.
- **Milestone 2 is not due** if AT1–AT6 fail. That is a withheld
  second payment, not a proved refund statute.
- **Milestone 1 refund** if work never starts after signing is an
  owner-private decision. This pack does not invent a rate or a
  cooling-off law.
- **Change order (written):** new target, extra family, extra days,
  or a metric threshold. Material change stops the 10-day clock until
  signed.
- **Upgrade path:** a change order may become the landed $30k / 30d
  pilot. Separately scoped. Not automatic.
- **Downgrade path:** see `pack.json` `offer.downgrade_path`. Failure
  Packet remains the fallback. Do not resurrect $500-first as the
  flagship (lost 3–1 in the synthesis).

## 5. Invoice field template

Fill these fields **inside an official invoicing UI** (for example
Stripe Dashboard invoices: https://docs.stripe.com/invoicing) or a
private invoice file. Never commit the filled values.

| Field | What goes there | Public Commons |
|---|---|---|
| invoice_id | minted by the seller | leave blank |
| invoice_date | date of issue | leave blank |
| seller_legal_name | owner-private payee | leave blank |
| seller_contact | owner-private | leave blank |
| buyer_legal_name | owner-private | leave blank |
| description | "White Box GGUF diagnostic, 10 calendar days, AT1–AT6" | this phrase is public |
| currency | USD | USD |
| line_1 | M1 before file — 6000 | amount is public; remittance is not |
| line_2 | M2 on AT1–AT6 — 6000 | amount is public; remittance is not |
| payment_terms | owner-private | `NOT_PROVIDED_ON_THIS_PAGE` |
| tax_line | owner-private determination | do not invent a rate or nexus |
| remittance | official provider invoice or owner-private bank UI | never paste here |

Stripe invoices are for a specific customer and are not reusable
payment links (`https://docs.stripe.com/invoicing`). This leftover
does not create one.

## 6. Contract / NDA / W-9 readiness checklist

Not legal representation. Not a determination that any form is due.

**NDA (unsigned checklist)**

- [ ] Parties named in a private document
- [ ] Scope: customer GGUF + harness + this diagnostic
- [ ] No hide-list dump; no public binary artifacts
- [ ] No publicity without written approval (`SOW_OUTLINE.md` §9)
- [ ] Term and return/destroy of customer files written privately

**SOW**

- [ ] This one-pager can be copied into a private SOW
- [ ] Target statement written before work
- [ ] AT1–AT6 copied as acceptance
- [ ] Not signed on Commons

**W-9 / tax**

- IRS publishes Form W-9, *Request for Taxpayer Identification Number
  and Certification*: https://www.irs.gov/forms-pubs/about-form-w-9
- [ ] Owner decides privately whether a requester needs a W-9
- [ ] TIN / SSN / EIN is entered only on the official form or the
  requester's private intake — never here
- [ ] This pack does not state backup-withholding, nexus, or sales-tax
  facts

**Entity / payee**

- Public provider string in `commercial.json` is "Muhlnickel / Bryce
  Muhlnickel". Whether that is the invoice payee is **UNMEASURED**.
- [ ] Owner chooses the legal payee in private records
