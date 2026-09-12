# CSU malt method expansion LIMS — build receipt

Task: `csu-malt-method-expansion-lims-01`
Builder: SOL-CSU-MALT / ChatGPT cloud seat
Date: 2026-09-09

## Scope and boundary

Synthetic/read-only malt receipt, weekly cutoff routing, package-to-method expansion, internal/third-party routing, QC gating, and staged reports. No production/vendor/customer write, compliance decision, outreach, prospect-facing demo, automatic report release, payment/spend, owner-PC action, force-push, or reset.

## Frozen acceptance

- 80 deterministic synthetic submissions: 60 complete before cutoff, 8 complete after cutoff, 12 defect rows.
- Exact statuses: 60 `CURRENT_WEEK`, 8 `NEXT_WEEK`, 4 `DUPLICATE_ID`, 4 `UNSUPPORTED_GRAIN_METHOD`, 4 `MISSING_IDENTITY_PACKAGE`.
- Ledger after first pass: 80 processed, 68 accessions, 130 unique jobs, 66 staged reports, 12 holds, 80 events.
- Exactly six `ASBC-PROTEIN` jobs route `THIRD_PARTY`; all other jobs route `INTERNAL`.
- Package→method expansion equals the frozen manifest for every accession.
- The one seeded QC breach batch (`QC-BREACH-01`) stages zero reports while retaining routed work evidence.
- Full same-ledger replay adds zero processed/accessions/jobs/reports/holds/events.
- Reports remain `STAGED_HUMAN_REVIEW`; anonymous release is rejected and named-human release returns a copy without mutating stored staged evidence.

Fixture SHA-256: `e44277351d09c14b7388e15f17fa0d0748f09b0cab614ca0d52c4f868365f2d4`
Manifest SHA-256: `db63d102bad9d00f55dbea50b0ddb799b01c916ae3a1850b363372033a167579`

## Verification actually run

Python: `Python 3.13.5`

- `python3 -m py_compile csu_malt_expansion.py test_csu_malt_expansion.py` — PASS.
- `python3 test_csu_malt_expansion.py -v` — 10/10 PASS.
- `python3 csu_malt_expansion.py --fixture fixtures/csu_80_submissions.json` — PASS with exact status/ledger/routing counts above and replay delta 0 for every ledger collection.
- Fixture-tamper regression — PASS (hash mismatch rejected).
- Human-release regressions — PASS (anonymous rejected; named release copy-only).

## Authored file SHA-256

- `README.md` — `2b39c57801f5b46f35ffd0b61570c0f619c8282f4534eb42ae7a016c773620b6`
- `csu_malt_expansion.py` — `95a80ee00bd60108369e85c9bad94acec576483777de17ef8abf32e0d73a679a`
- `test_csu_malt_expansion.py` — `2625056e6347063dc43a4047bda246195eab857c9dd7145dd2b6cdf3ba862b33`
- `fixtures/csu_80_submissions.json` — `e44277351d09c14b7388e15f17fa0d0748f09b0cab614ca0d52c4f868365f2d4`
- `fixtures/manifest.json` — `db63d102bad9d00f55dbea50b0ddb799b01c916ae3a1850b363372033a167579`

Publication receipts (PR/head/merge/current-main blob readback) are posted to the canonical Slack build-demand thread after guarded publication; this file does not self-edit to fabricate merge evidence.
