# BPHC Consultant Qualified Vendor Pool — Qualification Packet

This package turns the live Boston Public Health Commission consultant-pool RFP into a deterministic owner-review gate. It does not fabricate eligibility or submit anything.

## Opportunity

BPHC is creating a qualified consultant pool for Communications; Research, Evaluation & Assessment; Strategy & Planning; and Grant Writing. The official source says the pool can remain active for up to five years and pool inclusion does not guarantee work. The proposal deadline in the source is **Wednesday September 30, 2026 at 5:00 PM EST**.

The high-value characteristic is repeat access: qualified vendors can be considered for future program-specific scopes, budgets and timelines. The hard commercial constraint is equally important: BPHC requires prior public-health/nonprofit/government-funded experience and two professional references. This repository does not assume those facts are true for us.

## Files

- `source_snapshot.json` — canonical URLs plus extracted source facts; no fake PDF digest.
- `requirements.json` — fail-closed hard gates and preferences.
- `owner_inputs.template.json` — owner-only facts that must be completed outside source control.
- `response_outline.md` — RFP-aligned response skeleton and page limits.
- `evidence_inventory.md` — explicit proof gaps / evidence needs.
- `preflight.py` — deterministic `HOLD` / `READY_FOR_OWNER_SUBMISSION_REVIEW` compiler.
- `test_preflight.py` — hostile and lifecycle coverage.

## Safe workflow

1. Copy `owner_inputs.template.json` outside the repository to an owner-controlled location.
2. Fill it with current, supportable facts. Do not commit private reference contact details, secrets, or unsupported claims.
3. Refresh the official RFP/listing and update `source_snapshot.json` if terms changed.
4. Run:

```bash
python3 opportunities/bphc_vendor_pool_2026/preflight.py \
  --source opportunities/bphc_vendor_pool_2026/source_snapshot.json \
  --owner /path/to/private-owner-inputs.json \
  --trusted-now 2026-09-13T10:30:00Z
```

5. A `READY_FOR_OWNER_SUBMISSION_REVIEW` result means only that the deterministic completeness gates passed. Human owner review of qualifications, attachments, pricing, references, legal/compliance obligations, formatting and the final PDF is still required.

## Authority ceiling

The tool never sends email, registers with procurement, contacts references, certifies qualification, certifies SAM/living-wage status, commits pricing, accepts a contract, signs anything, or claims an award/revenue. All output authority flags remain false.

## Source freshness

The source snapshot expires for this gate after seven days. A stale snapshot returns `SOURCE_REFRESH_REQUIRED`. Deadline passage returns `DEADLINE_PASSED`. This is intentionally stricter than trusting a cached opportunity record.
