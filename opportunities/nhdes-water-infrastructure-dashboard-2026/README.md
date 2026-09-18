# NHDES Water Infrastructure Funding Dashboard — RFP DES 2026-23 carrier

Operation: `NHDES-WATER-INFRA-DASHBOARD-RFP-DES-2026-23-ZMCT8R3-20260913`

**State: `HOLD / QUALIFICATION_REQUIRED`. No proposal has been submitted. No contract, buyer acceptance or revenue is claimed.**

This carrier turns a live New Hampshire Department of Environmental Services procurement into an evidence-bound response package instead of a prose-only bid draft. The RFP is for a five-year public dashboard showing water-infrastructure investment through narratives, graphics, maps and searchable project data. The proposal deadline in the recovered RFP is September 25, 2026; the inquiry window ended September 4.

## Why this is worth pursuing

The technical vision is unusually compatible with the Commons/AquaTrace operating style: deterministic evidence, exact reconciliation, public-facing data quality and water-domain context. The buyer weights project understanding/vision/methodology/innovation at **40%**, the largest single factor. The lane is not automatically a prime-bid GO, however: **25%** is relevant firm experience/qualifications and the repo cannot manufacture that evidence.

## Delivered here

- `source_ledger.md` — recovered RFP/addendum facts and freshness rules.
- `qualification_matrix.md` — truth-bound GO/HOLD gates mapped to scoring and mandatory sections.
- `proposal_outline.md` — evaluation-mapped response architecture, technical vision, schedule, demo strategy and owner-input boundaries.
- `prototype/dashboard_projection.py` — deterministic projection/reconciliation core with accessibility/data-quality gates.
- `prototype/sample_projects.json` — explicitly synthetic data for demo/testing only.
- `cost_model.py` — transparent five-year cost sensitivity calculator with caller-supplied rates only.
- `readiness.json` + `readiness_gate.py` — fail-closed submission state. Current file intentionally blocks.
- `tests/` — hostile regression tests for money, identity, coordinates, accessibility, procurement exceptions and unauthorized contact.

## Prototype contract

Run:

```bash
python prototype/dashboard_projection.py \
  --input prototype/sample_projects.json \
  --output /tmp/nhdes_projection.json
```

The output includes exact aggregate cents, program/town/project-type totals, canonically sorted project records and the SHA-256 of the input bytes. Re-running the same bytes produces the same projection bytes.

The code intentionally rejects:

- duplicate project IDs;
- negative or non-integer funding cents;
- unsupported program/project categories;
- non-finite or obviously out-of-state coordinates;
- empty narratives;
- media without alternative text;
- non-HTTP(S) media URLs.

This is a prototype for a deterministic data/release layer, not a claim that NHDES supplied data has already been integrated.

## Five-year pricing scaffold

The RFP requires total/task cost and hourly staff rates. Never commit invented pricing. To explore an approved assumption set:

```bash
python cost_model.py \
  --year1-hours 900 \
  --maintenance-hours-per-year 80 \
  --hourly-rate 150 \
  --hosting-per-year 2400 \
  --other-fixed 5000
```

Those numbers are an **example invocation only**, not a recommended bid and not company-approved rates.

## Submission gate

```bash
python readiness_gate.py readiness.json
```

Current expected exit code is `2` (`BLOCKED`). A READY result requires explicit truth for bidder identity/signatory, contacts, personnel, previous dashboard evidence, platform/scope, rates, schedule, accessibility, hosting/handover, confidentiality review, final PDF inspection, current submission route and receipt-confirmation ownership.

If a P-37 or RFP exception is actually required, the gate stays blocked because the published inquiry period has already ended and the RFP says unraised exceptions are waived.

## Procurement safety rules

1. Re-download/recheck the current State bid listing and all addenda immediately before any real submission.
2. Do not contact NHDES program staff outside the RFP-authorized route; the solicitation has a communication restriction.
3. Do not describe this synthetic prototype as previous client work.
4. Do not invent firm credentials, references, rates, insurance, legal authority, accessibility certification or platform licenses.
5. Render and inspect the final proposal PDF; use the exact currently published recipient/subject; confirm receipt as the RFP instructs.
6. A send receipt is not an award; an award is not collected revenue.

## Source custody

Built by `Z-MobiusCairn-914015-T8R3` / GPT-5.6 Sol for the owner-authorized Commons revenue pipeline. Earlier durable semantically identical custody, if proven to predate the claim receipt, supersedes this lane.
