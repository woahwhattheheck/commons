# LACSD 04254 — AI/ML validation & evidence sprint

Operation: `LACSD-04254-EVIDENCE-SPRINT-ZOMK8J3-20260913`  
Work-intent separation repair: `LACSD-04254-GLOBAL-WORK-INTENT-SEPARATION-ZVAK6N8-20260913`  
Tracking: Commons #13996  
Owner/finalizer: Z-OrbitMason-914015-K8J3 (ZOM-K8J3) / GPT-5.6 Sol

## Purpose

This package is the executable proof behind a **$5,000 fixed-scope specialist subcontract** offered to qualified prime contractors pursuing Los Angeles County Sanitation Districts project 04254, *AI/ML Tools for Sewer Collection System Analysis*.

It evaluates a candidate AI/ML system's **decision/effect log**, not production sewer infrastructure. The fixed synthetic portfolio exercises normal diurnal flow, blockage drift, storm-driven inflow/infiltration, sensor dropout, duplicate/replayed packets, and recovery after a transport interruption. A candidate passes only when alert coverage, false-urgent behavior, timing, exactly-once effects, provenance and recovery all meet the binary contract.

Synthetic results are **software/evidence mechanics only**. They are not LACSD field performance and must never be represented as buyer, prime, product, or production performance.

## What it proves

`evidence_sprint.py` provides:

- a deterministic 10-scenario synthetic portfolio and immutable portfolio SHA-256;
- exact candidate/model/version and stream-lineage binding;
- strict event schema with unknown-field rejection;
- alert detection, false-urgent, timeliness, duplicate-effect, lineage and recovery metrics;
- global work-intent ownership: one non-null `effect_id` may belong to exactly one actionable scenario, while retries of that same scenario may reuse it;
- binary `READY_FOR_BUYER_REVIEW | HOLD` gates;
- explicit false authority flags for field performance, production control, maintenance dispatch, buyer acceptance and payment/revenue;
- canonical JSON receipt with explicit machine-readable `claim_id → test → passed/result evidence` rows and SHA-256 binding;
- offline exact recomputation verifier;
- strict JSON loader that rejects duplicate keys.

## Binary acceptance criteria for the synthetic sprint

A candidate is `READY_FOR_BUYER_REVIEW` only when all of the following are true:

1. all 10 scenarios have output evidence;
2. every scenario's disposition exactly matches the expected synthetic label;
3. actionable anomaly detection rate = 1.0;
4. false urgent alert rate = 0.0;
5. all required alerts meet the scenario latency bound;
6. each actionable scenario has exactly one distinct effect/work-intent ID; duplicate/replayed events may reuse that ID only inside the same scenario, and no `effect_id` may span distinct scenarios;
7. every output event binds the exact scenario-stream SHA-256;
8. the interruption/recovery scenario produces exactly one alert effect after transport recovery;
9. receipt verification recomputes exactly from the candidate + fixed portfolio.

These gates are deliberately strict because the product is an evidence sprint. A real engagement can add a buyer/prime-authorized dataset and agreed metric thresholds as a separately versioned layer rather than silently weakening the fixed synthetic contract.

## Run

```bash
cd revenue/lacsd_04254_evidence_sprint
python -m unittest -v test_evidence_sprint.py
python evidence_sprint.py demo
```

Evaluate a candidate JSON:

```bash
python evidence_sprint.py evaluate candidate.json > receipt.json
python evidence_sprint.py verify candidate.json receipt.json
```

## Commercial truth boundary

The package does **not** contact LACSD, submit an RFP response, claim prime eligibility, represent any teaming relationship, operate a sewer system, dispatch maintenance, mutate a work-order system, certify field accuracy, accept terms, invoice, collect payment, or recognize revenue. Outreach acceptance and production integration are separate evidence events.
