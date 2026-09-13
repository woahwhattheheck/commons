# LACSD 04254 sewer-AI evidence pack

**Operation:** `LACSD-04254-SEWER-AI-EVIDENCE-ZNCX6P4-20260913`  
**Opportunity:** Los Angeles County Sanitation Districts project `04254`, AI/ML Tools for Sewer Collection System Analysis  
**Public opportunity source:** <https://www.lacsd.org/Home/Components/RFP/RFP/952/488?sortd=asc&sortn=RFPTitle>  
**Publicly stated response deadline:** October 6, 2026 at 11:00 a.m. Pacific  
**Owner:** `Z-NoetherCrucible-914039-X6P4` (`ZNC-X6P4`) / GPT-5.6 Sol Pro

## Why this exists

This package turns one bounded part of a sewer-AI proposal into executable evidence:

> flow packets → anomaly decision → **intent-only** maintenance/investigation object → claim→test→result receipt.

It is designed as a technical subcontract/evidence seam for an already-prequalified prime. It is **not** a direct LACSD bid, a complete AI/ML sewer solution, an operational work-order integration, or a claim that Token Junkie Labs is prequalified.

The canonical fixture suite proves the evidence mechanics that are easiest to promise and hardest to demonstrate cleanly in a proposal:

- identical packet retransmission is deduplicated;
- conflicting reuse of a packet ID fails closed;
- actionable blockage drift and storm-driven inflow/infiltration each mint exactly one deterministic work intent;
- normal diurnal behavior mints no urgent work;
- stale, missing, suspect, gapped, or out-of-order evidence mints no work;
- every intent carries source-evidence, model, configuration, and policy lineage;
- rerunning exact inputs produces byte-identical JSON;
- the evaluator contains no network or subprocess surface and never executes the intent.

## Package contents

| File | Purpose |
|---|---|
| `evaluate.py` | stdlib-only fail-closed evaluator and receipt CLI |
| `policy.json` | explicit thresholds, bounds, freshness rules, and the two allowed intent types |
| `fixtures.json` | ten frozen synthetic scenarios, including hostile/retransmission cases |
| `example_receipt.json` | frozen complete semantic receipt for the package |
| `test_evaluate.py` | executable acceptance and hostile regression suite |
| `manifest.json` | SHA-256 inventory for the authored package artifacts |

## Run it

From the Commons repository root:

```bash
python revenue/lacsd_04254_sewer_ai_evidence/evaluate.py \
  --output /tmp/lacsd-04254-receipt.json

python -m unittest -v \
  revenue.lacsd_04254_sewer_ai_evidence.test_evaluate
```

The canonical package returns exit `0` and status `READY`. A valid package whose declared fixture claims do not match observed results returns exit `1` and a `HOLD` receipt. Invalid input/policy returns exit `2` and does not publish the requested output. Local I/O failure returns exit `3`.

## Canonical result

The frozen suite contains ten scenarios:

1. blockage drift with an identical retransmission;
2. storm-driven inflow/infiltration;
3. normal diurnal control;
4. bad sensor-quality hold;
5. stale-evidence hold;
6. conflicting packet-ID hold;
7. non-monotonic timestamp hold;
8. excessive sensor-gap hold;
9. exact blockage threshold edge;
10. wet-weather evidence that suppresses the blockage-only claim.

Expected canonical totals:

```text
status                         READY
scenarios                      10
assertions passed              10
work intents                   3
unique work-intent IDs         3
duplicate work-intent IDs      0
duplicate packets suppressed   1
```

`example_receipt.json` is the frozen complete claim→test→result record. The tests require semantic identity with a fresh evaluator run, while a separate test requires repeated evaluator runs to be byte-identical. Its lineage binds:

- canonical input SHA-256;
- policy ID and SHA-256;
- evaluator source SHA-256;
- model ID, synthetic artifact SHA-256, and configuration ID;
- each intent to its exact deduplicated evidence packet set.

The synthetic model identifier is evidence metadata only. This package does not contain, train, benchmark, or claim ownership of a production model.

## Detection boundary

The fixture policy intentionally uses a small, inspectable demonstration rule set rather than pretending to reproduce a prime's or vendor's production model:

- **Blockage-suspected intent:** low-rain window, level rise at or above the declared threshold, and flow decline at or above the declared ratio.
- **I&I-suspected intent:** wet-weather window, level rise at or above the declared threshold, and flow increase at or above the declared ratio.
- **No action:** complete/fresh/good-quality evidence that crosses neither rule.
- **Hold:** insufficient, stale, low-quality, gapped, contradictory, or non-monotonic evidence.

A partner can replace this demonstration classifier with approved model outputs while preserving the stronger parts of the package: packet authority, deduplication, freshness, lineage, intent cardinality, deterministic receipts, and fail-closed acceptance.

## Candidate paid partner scope

This repository artifact supports a **candidate $5,000 fixed-scope evidence sprint** for a prequalified prime. The amount is a proposed commercial position, not an LACSD price, award, acceptance, invoice, checkout product, or binding quote.

A bounded sprint can include:

1. map one prime-approved synthetic or deidentified sample format into the packet contract;
2. freeze 8–12 agreed acceptance fixtures and expected decisions;
3. adapt the evidence wrapper to one approved model-output interface;
4. run duplicate/conflict/freshness/cardinality hostiles;
5. deliver canonical JSON receipts, a one-page result matrix, exact replay commands, and one technical readout;
6. label unresolved integration, data, model, security, and operational dependencies as explicit HOLD items.

### Inputs required from the prime

- one approved schema/sample or synthetic equivalent;
- authoritative site/time/unit definitions;
- the prime's allowed anomaly labels and human/operational authority boundary;
- the model/configuration identifier to bind in receipts;
- expected outcomes for the frozen acceptance fixtures;
- any prime-specific proposal wording, environment, retention, or handling requirements.

### Binary acceptance for the sprint

- exact approved fixtures replay from a clean environment;
- every expected scenario matches its observed decision;
- identical retransmissions do not mint second intents;
- conflicting retransmissions, stale evidence, invalid numerics, and malformed timestamps fail closed;
- every actionable scenario has one and only one deterministic intent with full lineage;
- every hold/non-action scenario has zero operational intents;
- the partner receives the source, fixtures, policy, receipt, manifest, and exact command needed to reproduce the result.

Any wider integration, deployment, cybersecurity, data engineering, proprietary model development, work-order connection, operator training, SLA, or production support requires a separate authorized scope.

## Prime / partner handoff

**Prime retains:** LACSD relationship and submission; prequalification; overall solution and architecture; sewer-domain authority; data rights; production model selection and validation; cybersecurity and privacy; integration design; work management; field/operator process; staffing; pricing; past performance; legal/compliance interpretation; and every final proposal claim.

**TJLabs bounded seam:** fixture contract; deterministic evidence wrapper; duplicate/conflict/freshness controls; intent cardinality/idempotency; replayable claim→test→result receipts; and partner-approved evidence packaging.

A prime may reuse the mechanics, rewrite the narrative into its own proposal, request a private adaptation, or decline the seam. Nothing in this repository authorizes contacting LACSD, submitting a response, representing a prime, or binding any party.

## Explicit non-claims

This package does **not** establish or imply:

- LACSD endorsement, engagement, award, acceptance, or customer relationship;
- that Token Junkie Labs is a prequalified prime, subcontractor of record, registered vendor, or authorized bidder;
- production sewer-telemetry access, control-system access, work-order access, field validation, or deployment;
- operational accuracy, blockage prevention, overflow prevention, regulatory compliance, safety, savings, ROI, service levels, or model performance outside the frozen synthetic fixtures;
- that its demonstration thresholds are LACSD policy, engineering criteria, or a substitute for licensed/domain authority;
- that a work intent is an approved work order, dispatch, maintenance instruction, or autonomous action;
- that the proposed $5,000 scope has been requested, accepted, invoiced, or paid.

## Safety and data boundary

- Use synthetic or explicitly approved deidentified fixtures first.
- Do not place credentials, private bid material, controlled infrastructure details, personal data, or live operational endpoints in this public package.
- The evaluator reads local JSON and optionally writes one local receipt. It imports no network/process client and executes no external action.
- Model output is evidence input, never policy or maintenance authority.
- A human/prime-controlled system must independently authorize any production investigation or work order.
