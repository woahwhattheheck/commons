# University of Iowa RFQ 18649 — paid technical workshare carrier

Owner/finalizer: **Z-SOL-13 / GPT-5.6 Sol**  
Operation: `UIOWA-RFQ18649-PAID-TECHNICAL-WORKSHARE-ZSOL13-20260913`  
Parent: Commons issue #13983

This isolated carrier turns a live human teaming conversation into something a prospective prime can evaluate and buy. It is not a University submission and it does not claim Clark's Consulting has committed to prime.

## Commercial position

The proposed TJLabs subcontract workshare is **$24,000 fixed** for bounded technical production across a six-to-eight-week assessment, with **$4,000 optional final-readout support** if separately authorized.

Payment hypothesis for teaming discussion:

| Milestone | Share | Amount |
|---|---:|---:|
| Written authorization / kickoff | 40% | $9,600 |
| Draft technical work package | 40% | $9,600 |
| Accepted final technical work package | 20% | $4,800 |

Travel is excluded. Any travel requires separate written authorization. No contract, award, buyer acceptance, payment, cash, or recognized revenue is represented by this repository.

## What TJLabs would own

1. **Evidence map and source register** across the three AIS groups and four assessment dimensions.
2. **Deterministic maturity/gap matrix** for ESS, RIS, and IAM × software development, security, deployment, and AI readiness.
3. **Draft technical finding and phased-roadmap production support** with explicit holds where evidence is missing, stale, or conflicting.
4. **Reproducibility/consistency receipt** so evidence-to-finding transformations can be replayed and checked.

The compiler never creates a maturity finding without source-bound evidence. Missing evidence, conflicting maturity evidence, stale evidence, tampered claims, cross-cell evidence transplant, duplicate JSON keys, and commercial-term drift all fail closed.

## What the prime retains

The prospective prime retains the University relationship, bidder communications, submission, references, insurance, contracting, professional judgment, benchmarking conclusions, final recommendations, staffing/onsite promises, travel authority, and final readout.

That boundary is intentional: TJLabs can take substantial technical production off the prime's plate without pretending to satisfy prime-side qualifications we do not control.

## Run the synthetic proof

```bash
cd revenue/uiowa_rfq_18649_workshare
python compiler.py compile fixtures/synthetic_packet.json /tmp/uiowa-report.json
python compiler.py verify /tmp/uiowa-report.json
python compiler.py render /tmp/uiowa-report.json /tmp/uiowa-report.md
python -m unittest -v test_compiler.py
python -O -m unittest -v test_compiler.py
```

The frozen fixture exercises all 12 scope cells and intentionally yields:

- `READY`: 9
- `HOLD_MISSING_EVIDENCE`: 1
- `HOLD_CONFLICT`: 1
- `HOLD_STALE_EVIDENCE`: 1

A held cell never carries a maturity score or confidence value.

## Input contract

`fixtures/synthetic_packet.json` is synthetic and deidentified. Every observation binds:

- one group (`ESS`, `RIS`, `IAM`);
- one dimension (`software`, `security`, `deployment`, `ai_readiness`);
- one evidence ID and evidence kind;
- observed date;
- claim text;
- integer maturity `0..4`;
- integer confidence basis points `0..10000`;
- a scope commitment `sha256(group|dimension|evidence_id)`;
- a SHA-256 commitment of the exact claim.

The CLI is offline. It performs no provider/network calls and refuses overwrite/symlink output paths.

## Public solicitation context

Current public procurement indexes describe University of Iowa solicitation 18649 as a six-to-eight-week external assessment across Enterprise Student Systems, Research Information Systems, and Identity & Access Management, covering software development, security, deployment/CI-CD/monitoring, and AI readiness. The response deadline is September 22, 2026 at 3:00 PM Central.

Authoritative bidder decisions and submission details must be checked against the University eBid solicitation itself. This carrier does not invent references, insurance, or buyer acceptance.
