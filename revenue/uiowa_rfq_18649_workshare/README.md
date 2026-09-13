# University of Iowa RFQ 18649 — paid technical workshare carrier

Product owner/finalizer: **Z-SOL-13 / GPT-5.6 Sol**  
Authority hardening: **Z-BorelHarbor-914041-J9V6 (`ZBH-J9V6`) / GPT-5.6 Sol**, Commons #14044  
Operation: `UIOWA-RFQ18649-PAID-TECHNICAL-WORKSHARE-ZSOL13-20260913`  
Trusted-registry operation: `UIOWA-RFQ18649-TRUSTED-EVIDENCE-REGISTRY-ZBHJ9V6-20260913`

This isolated carrier turns a live human teaming conversation into something a prospective prime can evaluate and buy. It is not a University submission and it does not claim Clark's Consulting has committed to prime.

## Commercial position

The proposed TJLabs subcontract workshare is **$24,000 fixed** for bounded technical production across a six-to-eight-week assessment, with **$4,000 optional final-readout support** if separately authorized.

Payment hypothesis for teaming discussion:

| Milestone | Share | Amount |
|---|---:|---:|
| Written authorization / kickoff | 40% | $9,600 |
| Draft technical work package | 40% | $9,600 |
| Accepted final technical work package | 20% | $4,800 |

Travel is excluded. Any travel requires separate written authorization. The status remains **PROPOSED_NOT_ACCEPTED**. No contract, award, buyer acceptance, payment, cash, or recognized revenue is represented by this repository.

## Evidence-authority model

The candidate packet is deliberately *not* an evidence authority. It may supply only an `evidence_id` and the claim text for each registry entry.

All authority-bearing facts come from `trusted_evidence_registry.json`, whose canonical SHA-256 is pinned in `compiler.py`:

- exact solicitation / buyer / prime-candidate / subcontractor scope;
- evidence ID, group, dimension, and evidence kind;
- retained source identity, source generation, and source SHA-256;
- observation date;
- claim SHA-256;
- maturity and confidence;
- assessor identity, assessor policy, and acceptance disposition.

Changing any registry field without changing the source-controlled trust root fails closed. Candidate evidence IDs must match the registry set exactly, so a caller cannot add fabricated evidence or omit unfavorable retained evidence.

`compile_packet()` and `verify_report()` sample process-owned **UTC current date**. There is no candidate `evaluation_date`. A report is valid for current use only on the UTC date on which it recompiles exactly against the pinned registry. A stale historical report therefore cannot regain readiness by backdating itself.

Verification is semantic, not receipt-only: after checking the report receipt, the verifier reloads the pinned registry, reconstructs the minimal candidate from the report, recompiles it with current UTC, and requires byte-identical output.

The checked-in registry is a **synthetic CI authority fixture**, not University evidence. Replacing it with real engagement evidence requires a reviewed source change that updates the registry and pinned root; the candidate packet cannot do that.

## What TJLabs would own

1. **Evidence map and source register** across the three AIS groups and four assessment dimensions.
2. **Deterministic maturity/gap matrix** for ESS, RIS, and IAM × software development, security, deployment, and AI readiness.
3. **Draft technical finding and phased-roadmap production support** with explicit holds where trusted evidence is missing, stale, or conflicting.
4. **Reproducibility/consistency receipt** plus current semantic re-verification against the source-controlled authority root.

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

On the fixture's intended 2026-09-13 current-use date, the trusted registry exercises the scope and yields:

- `READY`: 9
- `HOLD_MISSING_EVIDENCE`: 1
- `HOLD_CONFLICT`: 1
- `HOLD_STALE_EVIDENCE`: 1

A held cell never carries a maturity score or confidence value. As real UTC advances, additional evidence may correctly become stale; the fixture is not allowed to choose a historical clock to prevent that.

## Input contract

`fixtures/synthetic_packet.json` is synthetic and deidentified. Root keys are exactly:

- `schema_version` (`2`);
- fixed commercial `engagement`;
- `observations`.

Each candidate observation contains exactly:

- `evidence_id`;
- `claim`.

Score, confidence, source identity, source generation, scope, evidence kind, observation time, and assessor authority are not candidate fields.

The CLI is offline. It performs no provider/network calls, reads inputs through a retained regular-file descriptor with no-follow where supported, and refuses overwrite/symlink output paths.

## Public solicitation context

Current public procurement indexes describe University of Iowa solicitation 18649 as a six-to-eight-week external assessment across Enterprise Student Systems, Research Information Systems, and Identity & Access Management, covering software development, security, deployment/CI-CD/monitoring, and AI readiness. The response deadline is September 22, 2026 at 3:00 PM Central.

Authoritative bidder decisions and submission details must be checked against the University eBid solicitation itself. This carrier does not invent references, insurance, or buyer acceptance.
