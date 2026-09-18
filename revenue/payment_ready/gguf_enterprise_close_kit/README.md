# GGUF $12k Enterprise Close + Delivery Kit

Operation: `GGUF-12K-ENTERPRISE-CLOSE-KIT-SOLZ-20260916`  
Owner/finalizer: **Sol-Z / GPT-5.6 Sol**

This directory is the buyer-evaluable close and fulfillment spine for the already-live Commons offer `gguf-diagnostic-10d-12k`. It does **not** mint a new offer, price, checkout, payment link, buyer, acceptance event, delivery event, or revenue claim.

## Canonical authority

Production compilation reads the current repository files directly:

- `revenue/payment_ready/pack.json`
- `revenue/payment_ready/recovery.json`
- recovery receipt schema: `revenue/payment_ready/receipt.schema.json`
- recovery transition authority: `host/revenue_recovery.py`
- public purchase-intent surface: `diagnostic.html`

The close kit fails closed unless the canonical source still binds:

- offer ID `gguf-diagnostic-10d-12k`;
- product `White Box diagnostic`;
- currency **USD**;
- **$12,000** fixed / **10 calendar days**;
- M1 **$6,000**, after NDA + SOW and before customer file exchange;
- M2 **$6,000**, **on AT1–AT6 acceptance**;
- acceptance rule `rollback evidence, not metric lift`;
- AT1 through AT6 in exact order; and
- `diagnostic.html` as an open purchase-intent-only surface with no payment collection on that page.

It also recomputes the canonical terms digest and the exact text digest of `pack.json`, requiring both to match the generation recorded by `recovery.json`. A caller cannot replace these with arbitrary SHA-shaped values and recompute a self-receipt.

## Recovery-runtime boundary

The existing recovery rail says exact artifact bytes, exact predecessor-source bytes, schema-bound stage facts, and deterministic runtime replay are transition authority. Private NDA/SOW/M1 bytes must come from a disjoint external evidence root, and their real-world order is owner-reported.

The close kit therefore **does not authenticate NDA, SOW, M1, buyer acceptance, delivery, or payment from standalone hashes**. A production intake that contains plausible 64-hex identifiers remains `HOLD_RECOVERY_REPLAY_REQUIRED`; the repository flags `nda_signed`, `sow_signed`, `m1_payment_received`, `private_file_transfer_authorized`, `customer_acceptance_recorded`, and `revenue_recognized` all remain false.

Current canonical recovery truth is also binding. As long as purchase intent is `NEEDS_BUYER` and delivery is `NOT_LANDED`, a production close packet cannot leap to a ready/accepted state.

## Metadata-only intake

`validate_intake()` accepts only safe metadata:

- opaque engagement/customer references;
- model SHA-256 + byte count + control attestation;
- harness name/version + frozen command/evaluation-suite hashes;
- bounded objective;
- public HTTPS contact URL without query/fragment;
- retention ≤30 days; and
- receipt-shaped recovery generation identifiers.

It rejects model bytes, private evaluation cases, credentials, signed-document bytes, private buyer contact data, card/bank/tax values, and processor credentials.

Two modes exist:

- `SYNTHETIC_REHEARSAL` — exercises evidence semantics only; never production-ready.
- `PRODUCTION` — remains HOLD until canonical recovery/runtime evidence is independently replayed outside this close-kit surface.

## AT1–AT6 semantic evidence

`evaluate_acceptance()` recomputes:

- **AT1:** original SHA-256 + byte count match intake;
- **AT2:** ablated/intervention SHA-256 differs from original;
- **AT3:** restored SHA-256 **and byte count** exactly equal original;
- **AT4:** baseline, ablation, and restore receipts each bind run kind, exact input artifact, frozen harness command, frozen evaluation-suite generation, and outcome-summary identity; each receipt digest is recomputed;
- **AT5:** report identity + concise finding + explicit limitations; and
- **AT6:** a retained delivery manifest exactly binds engagement, original/ablated/restored artifacts, all three semantic run receipts, and report identity; the manifest receipt digest is recomputed.

Three unrelated hashes are not AT4. A caller-chosen delivery receipt sitting beside a list of hashes is not AT6. A payment reference never changes acceptance.

## Close-packet semantics

`compile_close_packet(repo_root, intake, evidence)` loads canonical authority itself. It does **not** accept a caller-supplied authority packet.

With the shipped synthetic fixture, the strongest state is:

`SYNTHETIC_EVIDENCE_COMPLETE_NON_PRODUCTION`

With current real-world canonical recovery truth, production remains a `HOLD_*` state. Customer acceptance remains an external event.

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

- `SOW_ORDER_FORM.md` — reusable scope/AT1–AT6/exclusion/change-order content; not signed.
- `SECURITY_INTAKE.md` — data classes, private transfer boundary, retention, incident/HOLD behavior.
- `operating_manifest.json` — 10-day plan, customer/TJLabs responsibility split, hard stops, expansion boundary.
- `REPRESENTATIVE_REPORT.md` — explicitly synthetic/redacted output example.
- `fixtures/synthetic_intake.json` — `SYNTHETIC_REHEARSAL` metadata fixture.
- `fixtures/synthetic_delivery_evidence.json` — semantic run and delivery receipts; no customer/model bytes.

## Hard stops

Stop for: no customer GGUF control; no runnable/frozen harness; missing exact recovery-runtime authority before private file transfer; out-of-scope work; failed byte-exact rollback; public/method-leaking binary delivery; credentials routed through Commons; or a demand that metric lift replace the signed acceptance rule.

## Expansion

The separate same-GGUF **$30k / 30-day White Box pilot** may be discussed only after a real customer AT1–AT6 acceptance event. License/productization discussion comes only after paid delivery. Neither is automatically accepted here.

## Verification

From this directory:

```bash
python -m py_compile close_kit.py test_close_kit.py
python -m unittest -v test_close_kit.py
python -O -m unittest -v test_close_kit.py
```

The path-scoped workflow runs the same suite on Python 3.11 and 3.13. Queued, skipped, action-required, or absent hosted runs are reported literally and never represented as green.

## Synthetic evidence warning

The included fixture hashes are representative test values. They demonstrate that the carrier can recompute and reject tampered evidence. They do **not** prove a customer exists, a private file moved, a legal agreement was signed, an invoice/payment occurred, a model improved, a customer accepted, a delivery landed, or revenue was recognized.
