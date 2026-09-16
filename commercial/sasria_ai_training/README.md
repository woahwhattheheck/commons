# Sasria RFP2026/22 AI-training readiness carrier

A dependency-free, fail-closed teaming/readiness package for **Sasria SOC Ltd RFP2026/22 — Appointment of Service Provider for Artificial Intelligence Training**.

The package exists because the truthful TJLabs posture is **teaming-first / direct-prime HOLD** unless a qualified South African training lead supplies the missing procurement, accreditation, certification, training-history, reference, platform-access, pricing, signatory, and portal evidence.

## Source posture

- Official submission / query system: <https://procurement.sasria.co.za/>
- Solicitation: `RFP2026/22`
- Working close used by this carrier: **2026-09-17 12:00 SAST (UTC+02:00)**.
- The source-backed RFP working review used for this carrier described a ~170-person, 12-month, role-based AI training programme and a three-level evaluation process.

The official Sasria RFP and any official amendments control. This repository does not contain an authenticated buyer-document byte snapshot and must not be treated as the procurement source of record.

## Captured working requirements

### Governance / returnables gate

The compiler expects explicit truth for these returnables before the prime mandatory gate can pass:

- SBD 1 — Invitation to Bid;
- SBD 4 — Disclosure and Declaration;
- SBD 6.1 — Specific Goals;
- Annexure A — confidentiality / NDA;
- Annexure B — bid conditions / bidder details;
- Annexure C — shareholder information;
- Annexure D — experience / proposed project team;
- CSD report;
- B-BBEE certificate or sworn affidavit;
- technical proposal;
- financial proposal.

A missing or false item remains visible as `missing_required_returnables`; it is never inferred from a company name or software artifact.

### Mandatory technical evidence

The prime gate also requires supplied evidence for:

- alignment to at least one recognized AI-governance framework captured by this implementation (`ISO/IEC 42001`, `NIST AI RMF`, or `Gartner AI Governance Playbook`);
- training-body association/accreditation;
- recognized certification capability;
- one-year post-training AI-platform access.

Regulated-environment training, financial-services training, facilitator evidence, reference letters, and recent AI-training count are separately exposed as warnings/evidence because they affect competitiveness/scoring but are not silently promoted into mandatory eligibility here.

### Technical score boundary

The working buyer score categories are represented only as **externally supplied, evidenced scores**:

| Category | Cap |
|---|---:|
| Company profile | 20 |
| Project proposal and training methodology | 40 |
| Training personnel | 10 |
| Key-personnel CVs | 10 |
| Reference letters | 20 |

The working threshold is 70/100. `BuyerTechnicalScore` validates category completeness, caps, threshold, and evidence references. It **does not award points** based on prose or infer a buyer result.

### Role-pathway coverage

All six captured audiences require their own explicit pathway:

- executives and senior management;
- specialists and general employees;
- AI Navigators;
- AI project team;
- technical team;
- business process owners.

Each pathway must have learning outcomes, delivery modes, evaluation methods, and retained training artefacts. Missing or duplicate roles fail closed.

## Paid TJLabs seam

See [`TEAMING_WORKSHARE.md`](./TEAMING_WORKSHARE.md). The workshare is deliberately separated from the prime qualification gate. Its supported commercial state is only:

`PAID_SCOPE_TO_BE_AGREED`

The package rejects `FREE_DISCOVERY` or any other commercial state as a valid workshare. That does not create a contract or price; it prevents buyer-specific delivery from being represented as implicitly free.

## Response readiness versus submission authority

Two states are mechanically separate:

- `RESPONSE_ASSEMBLY_READY` means the captured prime mandatory gate, evidence-backed technical threshold, all six pathways, and paid workshare structure are complete.
- `SUBMISSION_READY` additionally requires explicit confirmation of a procurement-portal account, an authorized signatory, and prime approval to submit.

A technically strong packet with no submission authority therefore remains `HOLD` for submission.

## Claims boundary

This package does **not**:

- certify CSD or B-BBEE status;
- establish South African procurement eligibility;
- claim Microsoft or other training accreditation/certification authority;
- validate client references, facilitator qualifications, or financial-services experience;
- issue buyer technical scores;
- register a portal account or submit a bid;
- create a partnership, subcontract, award, invoice, payment, cash, or booked revenue;
- provide legal, tax, procurement, cybersecurity, privacy, or B-BBEE advice.

## CLI

The included fixture intentionally fails closed:

```bash
python -m commercial.sasria_ai_training.cli \
  commercial/sasria_ai_training/example_hold.json \
  --json-out /tmp/sasria-readiness.json \
  --markdown-out /tmp/sasria-readiness.md
```

Exit code is `0` only when `submission_status == SUBMISSION_READY`; ordinary `HOLD` returns `2`.

## Tests

```bash
python -m unittest discover -s tests -p 'test_sasria_ai_training.py' -v
```

The suite covers missing prime evidence, individual returnables, framework recognition, training-history warning semantics, score caps, boolean score rejection, the 70-point threshold, score provenance, missing/duplicate/incomplete role pathways, explicit paid-workshare state, response-vs-submission separation, fully synthetic submission readiness, and deterministic receipts.
