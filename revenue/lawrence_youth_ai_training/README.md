# City of Lawrence Youth AI Workforce Training — Qualification Gate

This package is an **internal qualification and teaming evidence gate** for MassHire Merrimack Valley Workforce Board / City of Lawrence FY27 Youth AI Workforce Training Services (`BD-27-1412-LAW26-LAW85-132652`). It does not contact the buyer, sign certifications, set a bid price, submit a proposal, process participant data, infer employer commitments, or claim an award/payment/revenue.

Official RFP:  
https://www.masshiremvwb.org/wp-content/uploads/FY27-COL-Youth-AI-Workforce-Training-RFP-8.19.26.pdf

The compiled source contract captures the published solicitation spine that is material to qualification: the October 1, 2026 11:00 ET proposal deadline; the 15 required proposal/minimum-qualification document families; the 15-part end-to-end workforce capability surface; the 100-point evaluation weights; the 18–25 Lawrence target population; the 12-month follow-up requirement; the RFP's explicit encouragement of collaborative proposals; and buyer-specific semantic requirements for current Good Standing and most-recent audit evidence.

## Why this exists

The opportunity is not honestly reducible to "we can teach AI." A responsive provider must cover recruitment, eligibility/enrollment, intensive case management, AI training, career readiness, work-based learning, industry credentials, placement, employer engagement, participant/fiscal reporting, and twelve-month follow-up. The RFP also requires a complete minimum-qualification packet before the program proposal is scored.

The public gate composes the original reviewed v1 parser as `_gate_base.py` with a narrow hardening layer for Q&A freshness, load-bearing partner semantics, and buyer-specific document semantic authority. The gate therefore produces one of four internal states:

- `PRIME_READY`: the supplied evidence says the bidder itself covers every compiled capability and every mandatory document, including special semantic checks, is ready.
- `COLLABORATIVE_READY`: every capability/document is covered, but at least one committed partner is load-bearing.
- `HOLD`: evidence is incomplete, stale, expired, semantically unverified, source updates are not current, the exact RFP byte commitment does not match, or a proposed partner is not committed.
- `NO_BID`: an explicit hard constraint exists or trusted evaluation time is at/after the proposal deadline.

These are **evidence states, not buyer/legal determinations**. Every receipt is `INTERNAL_QUALIFICATION_EVIDENCE_ONLY`.

## Source custody

`source_contract.json` is compiled into the implementation with canonical SHA-256:

`9f9176b1747389c2c5a982e3fe459f6db2465b0244099fc8e625239236d7116e`

That hash protects the extracted requirement matrix and the document-semantic policy from silent local mutation. It is intentionally **not** presented as the SHA-256 of the buyer's PDF.

The caller must separately capture the current official RFP bytes and supply their trusted SHA-256 out of band as `--expected-rfp-sha256`. The snapshot carries the observed `document_sha256`; mismatch is a `HOLD`. This prevents the evidence document from choosing its own trusted solicitation-byte identity.

The RFP says bidders are responsible for monitoring the MMVWB website for updates. `updates_checked_at` must therefore be no more than 24 hours old at evaluation, and `addenda_complete` must be explicitly true. Once the buyer's published Q&A deadline (September 29 at 4:00 PM ET) has passed, `questions_answers_complete` must also be true. Receipts expire for verification after one hour and cannot verify at/after the proposal deadline.

## Evidence model

The snapshot has five top-level fields:

- `schema`
- `source_capture`
- `bidder`
- `partners`
- `capability_evidence`

`bidder.documents` must contain **exactly** all compiled required document IDs, including program proposal C–E as well as the minimum-qualification/price package. Generic documents are authority-driving only when their status is `READY`, they have a SHA-256 evidence commitment, and any expiry is still in the future.

Two buyer-sensitive documents have an additional fail-closed semantic boundary:

- `certificate_good_standing`: a READY document must carry `semantic_authority` bound to the exact document SHA, identify the **Massachusetts Department of Revenue** as issuer, provide an issuance timestamp, and provide separate currentness-verification evidence. The compiled gate uses a **conservative internal** 30-day maximum issuance age and 24-hour maximum verification age. Those age windows are internal qualification safeguards; they are not represented as buyer-published validity periods.
- `audit_assurance_certification`: a READY document must carry `semantic_authority` bound to the exact document SHA, an explicit financial-statement/audit `period_end_at`, a `most_recent: true` commitment, and separate evidence proving that most-recent determination no more than 24 hours old at evaluation.

Missing semantic authority, wrong issuer, stale Good Standing issuance, stale semantic verification, a non-most-recent audit, or a semantic/document hash mismatch produces `HOLD`. The wrapper strips the semantic metadata before invoking the retained v1 parser, so the reviewed core parser remains byte-for-byte unchanged while the public authority surface becomes stricter.

Capability evidence is authority-driving only when it is `VERIFIED`, has a SHA-256 commitment, is not expired, covers only compiled requirement IDs, and comes from either the bidder or a declared partner. Partner evidence counts only when that partner has an active `COMMITTED` commitment receipt. A prospective/declined/expired partner cannot fill a capability gap.

`hard_constraints` are explicit operator declarations such as `CANNOT_DELIVER_12_MONTH_FOLLOWUP`; the gate never invents them.

## CLI

Evaluate:

```bash
python -m revenue.lawrence_youth_ai_training.cli evaluate snapshot.json \
  --evaluated-at 2026-09-13T10:00:00Z \
  --expected-rfp-sha256 <trusted-current-rfp-sha256>
```

Exit codes:

- `0`: `PRIME_READY` or `COLLABORATIVE_READY`
- `3`: `HOLD`
- `4`: `NO_BID`
- `2`: malformed/unreadable input

Verify a receipt against the same evidence plus fresh trusted time:

```bash
python -m revenue.lawrence_youth_ai_training.cli verify receipt.json snapshot.json \
  --verified-at 2026-09-13T10:30:00Z \
  --expected-rfp-sha256 <trusted-current-rfp-sha256>
```

## Authority boundary

The receipt hard-codes all of these to `false`:

- proposal submission
- external contact
- pricing
- certification signature
- participant-data use
- inferred employer commitments
- inferred contract award
- inferred payment
- inferred recognized revenue

A downstream proposal/submission workflow must independently obtain the actual current buyer package, signatures/certifications, organization facts, partner commitments, budget, and authorized send authority.

## Exact-byte tests

From repository root:

```bash
python -m unittest discover -s revenue/lawrence_youth_ai_training -t . -p 'test*.py' -v
python -O -m unittest discover -s revenue/lawrence_youth_ai_training -t . -p 'test*.py' -v
python -m py_compile \
  revenue/lawrence_youth_ai_training/__init__.py \
  revenue/lawrence_youth_ai_training/_gate_base.py \
  revenue/lawrence_youth_ai_training/gate.py \
  revenue/lawrence_youth_ai_training/cli.py \
  revenue/lawrence_youth_ai_training/test_gate.py
```

The exact-head 29-case focused hostile suite covers prime and collaborative readiness, Q&A publication freshness, non-load-bearing prospective partners, exact document/capability coverage, source identity/hash freshness, authority invariants, receipt tamper/replay, plus the review-blocking semantic cases: missing Good Standing authority, wrong DOR issuer, years-old certificate observed today, stale issuer verification, non-most-recent audit, stale most-recent verification, exact semantic/document hash binding, and semantic-evidence mutation during receipt verification.
