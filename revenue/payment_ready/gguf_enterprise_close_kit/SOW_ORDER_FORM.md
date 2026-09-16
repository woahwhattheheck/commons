# GGUF Diagnostic — SOW / Order-Form Content

**Canonical offer:** `gguf-diagnostic-10d-12k`  
**Public product:** White Box diagnostic  
**Term:** 10 calendar days  
**Fixed fee:** USD 12,000  
**Milestones:** USD 6,000 after NDA + SOW signing and before customer file exchange; USD 6,000 on AT1–AT6 acceptance  
**Acceptance rule:** rollback evidence, not metric lift

This file is reusable order-form content. It is **not** a signed SOW, buyer acceptance, invoice, payment instruction, or revenue record.

## 1. Engagement objective

TJLabs will perform one bounded diagnostic engagement on one customer-controlled GGUF using a customer-provided runnable evaluation harness. The purpose is to produce a reproducible baseline, diagnostic finding, bounded ablation/intervention evidence, byte-exact rollback, and an evidence packet that the customer can evaluate against AT1–AT6.

No minimum performance lift, quality score, benchmark gain, commercial outcome, production-readiness result, or model-improvement percentage is guaranteed. Acceptance is defined only by the evidence contract below.

## 2. Prerequisites before private file transfer

The customer must provide, through an owner-private channel outside Commons:

1. evidence that both parties have completed the applicable NDA;
2. evidence that the final SOW/order form has been signed by authorized representatives;
3. evidence that the USD 6,000 M1 payment has been received through the agreed private payment rail;
4. an attestation that the customer controls the GGUF and is authorized to provide it for this engagement; and
5. a runnable evaluation harness with a frozen command identity and evaluation-suite identity.

The Commons close-kit stores only non-secret receipt hashes for items 1–3. It never stores signed-document bytes, payment credentials, model bytes, private contact data, card/bank details, tax identifiers, API keys, or passwords.

## 3. Included work

TJLabs will:

- record the original GGUF SHA-256 and byte count before any modification;
- freeze the supplied harness command/evaluation-suite identity;
- execute and receipt the baseline harness run;
- perform the diagnostic localization described in the signed private scope;
- create one bounded ablated/intervention artifact;
- execute and receipt the ablation harness run;
- restore the original artifact and prove byte-exact identity by SHA-256 and byte count;
- execute and receipt the restore harness run;
- produce a concise finding with explicit limitations;
- produce a delivery receipt binding the required artifact/run/report hashes; and
- deliver the private evidence packet for customer review.

## 4. Excluded work

Unless added by a separately accepted change order, this engagement excludes:

- training, fine-tuning, model hosting, production deployment, inference hosting, or ongoing operations;
- guarantees of metric lift, benchmark improvement, latency, throughput, safety, revenue, or product outcome;
- public release of the customer GGUF, original/ablated/restored binaries, private evaluation cases, or method-leaking binary diffs;
- acquisition of customer credentials or production secrets;
- legal, tax, accounting, compliance, security-certification, or procurement advice;
- third-party license clearance or representation that the customer's model/data rights are valid; and
- the 30-day White Box pilot or any license/productization grant.

## 5. Acceptance tests

- **AT1 — Original hash:** SHA-256 and byte count of the customer-supplied GGUF are recorded before modification.
- **AT2 — Ablated hash differs:** the bounded ablated/intervention artifact has a SHA-256 different from AT1.
- **AT3 — Byte-exact restore:** restored SHA-256 **and byte count** exactly equal AT1.
- **AT4 — Customer harness evidence:** baseline, ablation, and restore run receipts exist under the frozen customer harness/evaluation identity.
- **AT5 — Finding:** a concise report states what was shown, what was measured, and the limitations.
- **AT6 — Delivery receipt:** the delivery receipt names/binds the required artifact, run, and report hashes.

A payment reference does not prove AT1–AT6. A metric increase does not substitute for AT1–AT6. The customer makes the acceptance decision as an external real-world event.

## 6. 10-day delivery plan

Day 1 gates owner-private NDA/SOW/M1 evidence and intake. Day 2 freezes AT1 and harness identity. Day 3 runs baseline. Day 4 localizes the bounded diagnostic. Day 5 produces the ablation and receipt. Day 6 develops bounded intervention evidence. Day 7 proves rollback. Day 8 reruns the restored artifact. Day 9 creates the finding/limitations. Day 10 delivers the hash-bound evidence packet for customer acceptance review.

See `operating_manifest.json` for exact required exits and HOLD states.

## 7. Stop / HOLD conditions

Work stops before or during delivery if any of the following is true: customer control cannot be attested; the harness is unavailable; NDA/SOW/M1 external evidence is missing before private file transfer; requested work exceeds signed scope; rollback is not byte-exact; delivery would require public model bytes or a method-leaking public diff; credentials are routed through Commons; or acceptance is changed into a guaranteed metric-lift requirement.

A HOLD is not failure to deliver a promised metric. It is the explicit safety/commercial boundary that prevents the engagement from silently changing scope or claiming proof it does not have.

## 8. Change orders

A scope request outside Section 3 requires a written change order accepted by both parties before work proceeds. The 10-day clock, price, and milestone treatment for changed scope must be stated in that change order; this template does not pre-authorize it.

## 9. Security and data handling

Commons receives metadata and receipts only. The actual customer GGUF and any confidential harness cases move, if at all, through the separately agreed owner-private external transfer channel after prerequisites. Default engagement retention is 10 days and must not exceed 30 days without a separately documented customer requirement. Deletion/return obligations in a signed NDA/SOW control if stricter.

## 10. Expansion path

After **real customer AT1–AT6 acceptance** on the same GGUF, the parties may discuss the separate `white-box-gguf-pilot-30d` offer. A license/productization discussion occurs only after paid delivery. Neither expansion is included or automatically accepted here.

## 11. Signature / payment boundary

Signature blocks, legal entity names, addresses, tax data, payout details, account/routing numbers, card data, and payment-provider credentials belong only in the applicable private signing/payment systems. Do not add them to this repository.
