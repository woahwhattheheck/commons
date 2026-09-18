# CSU malt replay/phase guard — repair receipt

Operation: `csu-malt-replay-phase-guard-20260909-01`
Source task: `csu-malt-method-expansion-lims-01`
Source PR: `#11153`
Independent review consumed: `5157213235`
Slack claim: `C0BTURDA3PW / 1788975101.706769`

## Scope

Only:
- modified `revenue/production-lims/csu-malt-method-expansion/csu_malt_expansion.py`
- modified `revenue/production-lims/csu-malt-method-expansion/test_csu_malt_expansion.py`
- this new receipt

No fixture, manifest, provider, customer, outreach, compliance decision, real record, production system, spend, TITAN, owner-PC, force-push, or history rewrite action.

## Fresh-main preimage

Publication base: `c57e1bcb62d135e77b98325729715ae0d41fd0c0`
Base tree: `616b87a5de2b696d5a7c5179fe8e776bb1760b10`
Source preimage Git blob: `9ea2d433946b5d331e89e93a3b075b4c9558b3ac`
Test preimage Git blob: `4668a32bdfea47736d102493e4c54216a5a92dbf`
This receipt path was absent on the publication base.

The source and test files were reconstructed from connector-read current-main bytes, and their Git object hashes matched those exact preimage blobs before modification. Main advanced repeatedly during work; every advance was re-audited on these owned paths before composing this repair.

## Reproduced review blockers

1. An unknown `received_phase` such as `MYSTERY_PHASE` fell through to `NEXT_WEEK`, mutating processed/accession/job/report/event state instead of failing closed.
2. A second row reusing an already-seen `submission_id` but changing payload fields such as `qc_batch` returned `IDEMPOTENT_REPLAY`, silently discarding the changed content.
3. A sample ID previously recorded only in HOLD state could later be accessioned by a distinct submission ID, leaving the held-sample identity namespace ambiguous.

## Repair

- Preserve the existing `Ledger.seen` set and add `seen_payloads` to bind each processed submission ID to the deterministic digest of its full synthetic payload.
- Exact duplicate payloads remain `IDEMPOTENT_REPLAY`; a reused submission ID with different payload now raises `SUBMISSION_ID_PAYLOAD_MISMATCH` without ledger mutation.
- `received_phase` is explicitly restricted to `BEFORE_CUTOFF` or `AFTER_CUTOFF`; unknown phases raise `RECEIVED_PHASE_INVALID` before any processed/accession/job/report/hold/event mutation.
- Nonempty sample IDs are reserved across both accessioned and held samples, so a later distinct submission using a held sample ID classifies `DUPLICATE_ID` and does not accession it.
- The frozen deterministic package expansion, QC block, route split, report staging, release-copy behavior, fixtures, and manifest remain unchanged.

## Acceptance

Executed against exact candidate bytes in the cloud runtime:

- `python3 -m py_compile csu_malt_expansion.py test_csu_malt_expansion.py` — PASS.
- `python3 test_csu_malt_expansion.py -v` — **13/13 PASS**, zero failures/errors.
- `python3 csu_malt_expansion.py` — PASS with the original frozen result unchanged: 80 processed; 60 `CURRENT_WEEK`; 8 `NEXT_WEEK`; 4 `DUPLICATE_ID`; 4 `UNSUPPORTED_GRAIN_METHOD`; 4 `MISSING_IDENTITY_PACKAGE`; 68 accessions; 130 jobs; 66 staged reports; 12 holds; 80 events; exactly 6 third-party `ASBC-PROTEIN` jobs; one QC-breach batch; full replay delta zero.

New regressions prove:
- unknown cutoff phase fails closed with exact ledger equality before/after;
- changed payload under a seen submission ID fails closed while an exact payload replays idempotently;
- a held sample ID remains reserved across a later distinct submission.

Candidate Git blobs:
- source `dd02ee95fe2a5211aa810975b1e77cf6a0f1aaae`
- tests `193cc0be3b49859fd4f592381d933e510d1ccac8`

No production or external action is claimed by this repair.
