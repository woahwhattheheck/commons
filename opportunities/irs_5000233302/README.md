# IRS 5000233302 — partner-first capture packet

**Operation:** `IRS-5000233302-PARTNER-FIRST-ZSOL17-20260917`  
**Canonical issue:** Commons #15839  
**Posture:** **PARTNER FIRST / PRIME HOLD**  
**Opportunity:** IRS Sources Sought 5000233302 — Enterprise Data Pipeline Modernization and Data Consumption Services  
**Public response deadline:** 2026-09-25 2:00 PM ET  
**Anticipated value:** $15M–$20M, market-research estimate only

This subtree converts a live federal market-research notice into a truthful specialist-workshare capture packet. It does **not** assert that Token Junkie Labs can prime the requirement, holds a federal vehicle, has a qualifying UEI/size/socioeconomic status, has the required federal past performance, or has been accepted by any partner.

## Why partner-first

The notice asks respondents whether they can perform the full Draft PWS as prime and, if not, which functional areas they can perform. It also explicitly asks about teaming/subcontracting. The contemplated program spans Databricks/AWS data engineering, mainframe/legacy integration, governance/security, BI, AI-assisted modernization, DevSecOps, production operations, and key-person staffing. That makes a bounded specialist workshare truthful and economically meaningful while owner/prime qualifications remain unproven.

## Bounded offer

Internal commercial hypothesis: **$50,000 fixed, PROPOSED_NOT_ACCEPTED** for the **Legacy-to-Databricks Pipeline Acceptance & Migration Evidence Desk**.

The desk is limited to:
- source-to-target mapping QA and exception ledgers;
- deterministic pipeline acceptance/replay/idempotency evidence;
- data-quality and reconciliation evidence;
- requirements-to-test-to-release traceability;
- migration/cutover/rollback proof packets;
- operator reproducibility handoff.

The prime keeps Government-facing authority, staffing/key-person commitments, federal security/compliance, production credentials, architecture/deployment authority, Government pricing/invoicing, and final acceptance/O&M.

## Partner order

1. **Maximus Federal Services** — first qualification target because public award data ties Maximus to the prior IRS EDP delivery neighborhood, while Maximus currently publishes a first-party Small Business and Strategic Partnership Office route. **Current pursuit of 5000233302 is UNKNOWN.**
2. **Booz Allen Hamilton** — first-party supplier/small-business route and broad current federal vehicle access; **current pursuit is UNKNOWN.**
3. **Chevo Consulting** — public subcontract history on the prior IRS EDP award; route and current pursuit remain **UNKNOWN/HOLD**.

No public-fit fact is treated as consent, relationship, pursuit, acceptance, or send authority.

## Files

- `source_snapshot.json` — public opportunity facts + absolute authority ceiling.
- `requirements.json` — truth/authority gates and bounded workshare.
- `owner_inputs.template.json` — facts only the owner can establish; deliberately UNKNOWN/placeholder by default.
- `partner_shortlist.json` — evidenced partner candidates with participation explicitly UNKNOWN.
- `MAXIMUS_WORKSHARE_20260917.md` — bounded paid workshare for the primary target.
- `preflight.py` — deterministic, fail-closed internal packet compiler.
- `acceptance_harness.py` + `fixtures/` — synthetic-only executable reconciliation proof; receipts exclude row values.
- `tests/test_preflight.py` — source drift, deadline, owner-claim, partner-route, and authority hostiles.

## Run

```bash
python opportunities/irs_5000233302/preflight.py \
  opportunities/irs_5000233302/source_snapshot.json \
  opportunities/irs_5000233302/owner_inputs.template.json \
  opportunities/irs_5000233302/partner_shortlist.json

python -m unittest opportunities.irs_5000233302.tests.test_preflight -v
python -m unittest opportunities.irs_5000233302.tests.test_acceptance_harness -v
python -O -m unittest discover -s opportunities/irs_5000233302/tests -v

python opportunities/irs_5000233302/acceptance_harness.py \\
  opportunities/irs_5000233302/fixtures/synthetic_pass.json
```

A `PARTNER_PACKET_READY` receipt is **not** permission to contact anyone. Before any external message or form action: fresh Slack + Gmail relationship/collision census → exact Muse arbitration for target × route × purpose → provider action only after the live atomic contract returns explicit authorization. Provider-SENT then becomes DNR until a genuine external event.
