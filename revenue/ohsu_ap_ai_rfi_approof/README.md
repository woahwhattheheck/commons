# APProof — OHSU AP AI RFI recovery carrier

`APProof` is the reconstructed publication carrier for the September 13, 2026
`OHSU-AP-AI-RFI-20260923` workstream. The original Z-Sol seat owns the product,
specification, and first local implementation credit; ZKE-R9V2 reconstructed and
published it after the original receipt said GitHub quota blocked publication.

## Public opportunity context

Oregon Health & Science University's public bids page lists **RFI-2027-0824,
Artificial Intelligence-Enabled Accounts Payable Automation Solution**, for an
on-premises **Oracle E-Business Suite R12** environment. The public summary asks
respondents to discuss invoice intake/validation, matching, coding/approvals,
Oracle transaction processing, supplier/internal inquiries, statement
reconciliation, exception management, reporting/audit controls, comparable
experience, implementation needs, expected outcomes, and indicative pricing.
The public page lists a response deadline of **2026-09-23 17:00 Pacific**.

This repository does **not** claim to contain the controlling RFI package, an
OHSU response, OHSU data, Oracle credentials, production Oracle experience, or
buyer acceptance. Any submission still requires the controlling buyer package
and owner review.

## What the carrier does

APProof accepts owner-supplied JSON evidence and deterministically computes:

* strict invoice source validation and line-total reconciliation;
* duplicate economic-invoice holds;
* PO/vendor/currency/line/price/quantity matching;
* receipt-quantity checks for three-way-match evidence;
* non-PO coding-review holds;
* approval missing/pending/rejected holds;
* supplier-statement reconciliation in both directions;
* currency-separated deterministic metrics;
* a **shadow-only** Oracle staging projection;
* a SHA-256 hash chain over every emitted result and the authority ceiling;
* exact semantic verification by recompiling from the packet.

The Oracle projection is deliberately not an ERP integration. Every row says
`mode=SHADOW_ONLY`, has no Oracle transaction id, and keeps
`posting_authorized=false`.

## Authority ceiling

The compiler cannot:

* write to Oracle EBS or any other ERP;
* approve invoices or release payments;
* contact suppliers or internal users;
* send an OHSU response;
* assert an award, payment, cash receipt, or recognized revenue.

Those are data-level hard-false fields in every projection, not prose-only
promises.

## CLI

```bash
python -m revenue.ohsu_ap_ai_rfi_approof.cli compile fixture.json > projection.json
python -m revenue.ohsu_ap_ai_rfi_approof.cli verify fixture.json projection.json
```

A successful verification prints `OK`. Input or verification failures exit `2`.

## Truthful commercial posture

The September 13 receipt recorded an indicative model of `$15k discovery /
$85k shadow pilot / $180k–$350k implementation / $72k–$180k annual support`.
Those are **historical proposed ranges only**, not a quote, acceptance, contract,
award, receivable, payment, or revenue. They remain outside compiler authority.

## Test boundary

The root test suite exercises normal and optimized-interpreter semantics,
input strictness, duplicate/PO/receipt/approval/statement exception behavior,
determinism, tamper rejection, CLI round-trip, and 1,000 randomized safety
packets proving no generated result can promote external authority.
