# Redmond ECM evidence-contract compiler

This package is a deterministic, buyer-safe readiness compiler for **City of Redmond RFP 10915-26 — Enterprise Content Management Software and Implementation Services**.

It is deliberately not a proposal generator and not an ECM-platform claim. It is a reusable evidence/governance layer for an experienced ECM prime/vendor or technical subcontract team.

## Official procurement facts retained by the profile

- Official posting: `https://www.redmond.gov/bids.aspx?bidID=354`
- Official RFP: `https://www.redmond.gov/DocumentCenter/View/43368`
- Status rechecked 2026-09-14: **OPEN**
- Proposal due: **2026-10-02 4:00 PM Pacific**
- RFP body identifies these core areas: Technology, AI Governance, General Functionality, Records Management & Document Storage, Data Governance, Scanning, Workflow, Retention and Compliance, Records Search, Public Records Requests, and Reporting.
- RFP requires a proposal PDF, Exhibit A and C in Word, and Exhibit B in Excel.
- Exhibit A is the authoritative key-requirements line-item form. This compiler's retained profile intentionally covers only requirements explicitly stated in the RFP body and does not pretend to replace Exhibit A.

The retained `profile.json` SHA-256 at build time is:

`bdd59cdfe43963e4b23c53d169ee8441874acbe00895a39a2d0143d9b5b5a337`

## Why this exists

A proposal team needs to distinguish five very different things:

1. a current capability that has actual evidence;
2. support that depends on a third party or customization;
3. roadmap-only functionality;
4. unknown/unsubstantiated claims;
5. explicit blockers or contradictions.

Treating all five as "yes" creates proposal risk. The compiler instead maps supplier evidence into deterministic states:

- `met`
- `partial`
- `unknown`
- `blocker`

A critical unknown, explicit not-supported rating, future-only critical claim, or contradiction causes overall `BLOCKED`.

## Input contract

Input JSON has exactly three top-level keys:

```json
{
  "vendor": {
    "name": "Example ECM Prime + TokenJunkieLabs evidence accelerator",
    "role": "subcontractor",
    "scope_notes": "Synthetic example only."
  },
  "responses": [
    {
      "requirement_id": "RET-001",
      "rating": "Y",
      "comment": "Current retention behavior is evidenced.",
      "evidence_ids": ["EV-RET"]
    }
  ],
  "evidence": [
    {
      "id": "EV-RET",
      "kind": "test",
      "source_ref": "artifact://retention-test",
      "statement": "Retention test result retained by the proposal team.",
      "effects": [
        {"requirement_id": "RET-001", "effect": "support"}
      ]
    }
  ]
}
```

Allowed vendor ratings mirror the RFP response format: `Y`, `3P`, `C`, `F`, `N`, and `NA`.

Evidence effects are `support`, `constraint`, or `contradiction`. A `Y` with no linked supporting evidence is never promoted to `met`.

## Run

```bash
python revenue/redmond_ecm_evidence/compiler.py \
  --input revenue/redmond_ecm_evidence/fixtures/vendor_example.json \
  --json-out /tmp/redmond-ecm-report.json \
  --md-out /tmp/redmond-ecm-report.md
```

Both output paths are create-exclusive; existing files are refused. Input files must be regular non-symlink files. The CLI has no network access and exposes no submission, email, buyer-contact, or caller-time controls.

## Output

The JSON artifact contains:

- solicitation/profile identity and SHA-256;
- evaluation weights from the RFP;
- compliance matrix;
- blocker ledger;
- contradiction ledger;
- acceptance-test plan tied one-to-one to retained requirements;
- evidence catalog;
- explicit authority boundary;
- stable report SHA-256.

The Markdown artifact is a human-review rendering of the same compiled decision.

## Validation

```bash
python -m py_compile   revenue/redmond_ecm_evidence/compiler.py   revenue/redmond_ecm_evidence/test_compiler.py

python revenue/redmond_ecm_evidence/test_compiler.py -v
python -O revenue/redmond_ecm_evidence/test_compiler.py -v
```

The regression suite covers fail-closed critical unknowns, unsupported/future-only blockers, contradiction handling, partial support, duplicate/invalid IDs, stable ordering, strict JSON duplicate-key rejection, symlink refusal, create-exclusive output, deterministic rendering, and CLI authority boundaries.

## Commercial boundary

Use this package as a **paid ECM implementation/evidence/governance accelerator or technical subcontract** for an experienced prime/vendor.

It does not:

- submit a Redmond proposal;
- accept City terms;
- contact the City or any prospect;
- invent references, certifications, platform capability, pricing, or buyer approval;
- claim TokenJunkieLabs is a complete ECM product vendor;
- assert payment, cash, award, or recognized revenue.

See `COMMERCIAL_HANDOFF.md` for the prime/vendor handoff.
