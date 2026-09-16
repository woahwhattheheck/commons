# GGUF $12k Enterprise Close + Delivery Kit

Operation: `GGUF-12K-ENTERPRISE-CLOSE-KIT-SOLZ-20260916`  
Owner/finalizer: **Sol-Z / GPT-5.6 Sol**

This directory is the buyer-evaluable close and fulfillment spine for the already-live Commons offer `gguf-diagnostic-10d-12k`. It does **not** mint a new offer, price, checkout, payment link, buyer, acceptance event, or revenue claim.

## Canonical offer authority

The engine reads the existing current-repository authorities:

- `revenue/payment_ready/pack.json`
- `revenue/payment_ready/recovery.json`
- public surface: `diagnostic.html`

It fails closed unless they still say:

- offer ID `gguf-diagnostic-10d-12k`;
- public product `White Box diagnostic`;
- USD **12,000** fixed / **10 calendar days**;
- M1 = USD **6,000** after NDA + SOW and before customer file exchange;
- M2 = USD **6,000** on AT1–AT6 acceptance;
- acceptance = **rollback evidence, not metric lift**;
- AT1 through AT6 in canonical order; and
- the public surface remains an open **purchase-intent-only** road with no payment collection on that page.

This last point matters: the live GGUF page is not a $12k Stripe checkout. The existing canonical pipeline routes payment/provider work through private owner/provider surfaces. This kit preserves that instead of inventing a new checkout URL.

## What is now executable

`close_kit.py` provides four deterministic stages.

### 1. Canonical authority bind

`load_authority(repo_root)` reads the current `pack.json` and `recovery.json`, checks price/term/milestones/acceptance/rail boundaries, records their canonical JSON digests, and returns a receipt-bound authority packet. A caller-supplied authority packet is semantically revalidated; recomputing its checksum after changing price or rail semantics does not make it valid.

### 2. Metadata-only qualification intake

`validate_intake()` accepts only safe metadata:

- opaque engagement/customer references;
- model SHA-256 + byte count + control attestation;
- harness name/version + frozen command/evaluation-suite hashes;
- bounded objective;
- public HTTPS contact URL without query/fragment;
- retention ≤30 days; and
- opaque external evidence receipt hashes for NDA, SOW and M1.

It does not accept model bytes, private evaluation cases, credentials, signed-document bytes, private buyer contact data, card/bank/tax values, or processor credentials. Even when all three prerequisite receipt hashes are present, the generated packet keeps `nda_signed`, `sow_signed`, `m1_payment_received`, and `private_file_transfer_authorized` false. Those are external facts for an owner/human/provider to verify.

### 3. AT1–AT6 evidence compiler

`evaluate_acceptance()` recomputes:

- **AT1:** original SHA-256 + byte count match the frozen intake;
- **AT2:** ablated/intervention SHA-256 differs from original;
- **AT3:** restored SHA-256 **and byte count** exactly equal original;
- **AT4:** baseline/ablation/restore harness-run receipt hashes are distinct;
- **AT5:** finding has a report hash, concise statement and explicit limitation(s); and
- **AT6:** the delivery receipt binds the required artifact, run and report hashes.

A payment reference is parsed separately and never changes the acceptance tests. Passing AT1–AT6 yields only `AT1_AT6_EVIDENCE_READY_FOR_CUSTOMER_REVIEW`; it never records customer acceptance.

### 4. Close packet + semantic verifier

`compile_close_packet()` combines canonical authority, intake and optional delivery evidence. The strongest possible generated state is `READY_FOR_CUSTOMER_ACCEPTANCE_REVIEW`. `verify_close_packet()` recompiles the complete packet from retained sources and rejects caller status tampering.

Every generated packet keeps these false:

- `buyer_contact_authorized`
- `private_file_transfer_authorized`
- `nda_signed`
- `sow_signed`
- `m1_payment_received`
- `customer_acceptance_recorded`
- `invoice_authorized`
- `payment_mutation_authorized`
- `revenue_recognized`

## Buyer-facing material

- `SOW_ORDER_FORM.md` — reusable SOW/order-form content, AT1–AT6, exclusions, change-order and signature/payment boundaries.
- `SECURITY_INTAKE.md` — data classes, customer confirmations, private transfer boundary, retention, incident/HOLD behavior.
- `operating_manifest.json` — exact 10-day plan, customer/TJLabs responsibility split, eight hard stops, security contract and expansion boundary.
- `REPRESENTATIVE_REPORT.md` — redacted synthetic example showing what the customer receives and how rollback evidence is presented.
- `fixtures/synthetic_intake.json` — metadata-only synthetic qualification fixture.
- `fixtures/synthetic_delivery_evidence.json` — synthetic AT1–AT6 evidence fixture; no customer/model bytes.

## Hard stops

The operating manifest stops for: no customer GGUF control; no runnable/frozen harness; missing external NDA/SOW/M1 receipts before private file transfer; out-of-scope work; failed byte-exact rollback; public/method-leaking binary delivery; credentials routed through Commons; or a demand that metric lift replace the signed acceptance rule.

A HOLD is an explicit commercial/technical boundary, not permission to quietly broaden scope.

## Expansion

The existing next offer remains the same-GGUF **$30k / 30-day White Box pilot**, discussed only after a real customer AT1–AT6 acceptance event. License/productization discussion comes only after paid delivery. Neither expansion is automatically included or accepted by this kit.

## Verification

From this directory:

```bash
python -m py_compile close_kit.py test_close_kit.py
python -m unittest -v test_close_kit.py
python -O -m unittest -v test_close_kit.py
```

The path-scoped GitHub workflow runs the same semantic suite on Python 3.11 and 3.13. A queued, skipped, `action_required`, or absent hosted run is reported literally and never represented as green.

## Synthetic evidence warning

The included fixtures/report are intentionally synthetic. Their hashes are representative values used to exercise the contract. They prove the carrier can fail closed and assemble an evidence-shaped packet; they do **not** prove a customer exists, a private file moved, a model improved, a customer accepted, a payment occurred, or revenue was recognized.
