# MCC 1017-27 — collaborative AI workspace partner-first pursuit

Status: INTERNAL RESEARCH / PARTNER-FIRST / NO OUTBOUND

Current machine state is intentionally fail-closed:

- buyer authoritative package: EMPTY
- direct-prime evidence: EMPTY
- direct-prime readiness: false
- partner candidate Presidio: PUBLIC_FIT_ONLY
- proposed TJLabs workshare: $24,000 fixed / PROPOSED_NOT_ACCEPTED
- partner contact: false
- buyer contact: false
- portal mutation: false
- proposal submission: false
- award/payment/revenue: false

The live discovery target is Metropolitan Community College (Kansas City, Missouri) IFB 1017-27, Cloud-Based Collaborative AI Workspace Software. Secondary procurement indexing currently reports an October 5, 2026 response deadline and a September 25, 2026 questions deadline, plus a five-year relevant-experience gate and three higher-education references. Those facts remain SECONDARY_DISCOVERY until the literal Public Purchase package, addenda and Q&A are retained and hashed.

## Why partner-first

No retained evidence here proves that TJLabs has the indexed five years of qualifying enterprise/higher-ed SaaS/cloud-AI experience or three acceptable higher-education references. The gate therefore cannot reach direct-prime readiness while the controlling buyer package is absent.

Presidio is recorded only as a public-capability candidate. Its current first-party material describes a dedicated education practice, higher-education delivery examples, cloud/data/AI services, and a 2026 University of Michigan AI/data-science collaboration. None of that establishes intent to bid, MCC eligibility, acceptable references, willingness to prime, or acceptance of TJLabs' workshare.

## Carrier

- current_packet.json — source-bound current truth
- research_secondary.json — exact internal snapshot of secondary procurement discovery
- partner_presidio_public_fit.json — exact internal snapshot of first-party public capability facts
- pursuit_gate.py — deterministic compiler/verifier with hard-false external authority
- test_gate.py — hostile proof
- sources.md — authority separation and buyer-package gap
- partner_matrix.md — candidate qualification matrix
- paid_workshare.md — bounded $24k implementation/assurance scope
- decision_checklist.md — exact next gate before any external action

## Run

From repository root:

    python -m unittest -v test_mcc_1017_27_ai_workspace_20260917.py
    python -O -m unittest -v test_mcc_1017_27_ai_workspace_20260917.py
    python -m py_compile revenue/mcc_1017_27_ai_workspace_20260917/pursuit_gate.py revenue/mcc_1017_27_ai_workspace_20260917/test_gate.py test_mcc_1017_27_ai_workspace_20260917.py

Compile the current internal state with an explicit evidence time:

    python revenue/mcc_1017_27_ai_workspace_20260917/pursuit_gate.py revenue/mcc_1017_27_ai_workspace_20260917/current_packet.json --evaluated-at 2026-09-17T21:25:00-04:00

Expected current state: HOLD_MISSING_BUYER_PACKAGE.

## Authority ceiling

This package performs internal research, qualification, workshare planning and evidence checking only. It does not authorize contact, Public Purchase activity, proposal submission, signature, spend, award, payment, cash, or recognized revenue. A future external touch requires a fresh provider/relationship census and a new single-writer arbitration for the exact recipient × opportunity × purpose.
