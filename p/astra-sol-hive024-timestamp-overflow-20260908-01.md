# ASTRA-SOL Hive024 timestamp normalization follow-up

- Follow-up to merged PR #10678 (`4ebec486ab32439b4da59c60f1b7af57c39a7d5d`).
- Post-merge claim: PR #10678 comment `5585179236`; collision-hygiene refinement `5585195061`.
- Owned production path: `revenue/hive/niche-newsletter-publication/app.py`.
- New regression path: `revenue/hive/niche-newsletter-publication/test_timestamp_boundaries.py`.
- Original `test_app.py` remains byte-identical.

## Defect

`iso_utc()` parsed aware ISO strings under a `ValueError` guard, but performed `astimezone(UTC)` outside it. Valid aware datetime endpoints whose offsets normalize beyond year 1/year 9999 therefore raised bare `OverflowError` and escaped the HTTP route's `Problem`/SQLite handlers.

Reproduced values:
- `0001-01-01T00:00:00+14:00`
- `9999-12-31T23:59:59-14:00`

## Repair

Keep syntax and timezone validation unchanged. Wrap only UTC normalization/serialization `ValueError`/`OverflowError` and convert them to the existing `Problem(422, "<label> must be an ISO date-time")` contract.

## Evidence

A direct executable harness using the landed function shape reproduced bare `OverflowError: date value out of range` for both endpoint inputs. The candidate function returned `Problem(status=422)` with the existing ISO-date-time message for both.

The additive regression imports the real app and covers:
- direct min/+14 endpoint -> 422 Problem;
- direct max/-14 endpoint -> 422 Problem;
- real loopback POST `/api/sources` min/+14 `observed_at` -> JSON 422;
- real loopback POST `/api/issues` max/-14 `scheduled_at` -> JSON 422 after a valid source is created.

No full Commons-battery, browser, provider, send/schedule, or external-network claim is made by this receipt. Hosted PR results are recorded on the PR when available.

## Candidate identities

- Fresh-main checkpoint: `247049ef474ebbe65a08f1ac15a4cf0bd5cbb8d4`
- Base tree: `fdb199b562eb8922d5decba964eb042d8252f277`
- Original app blob: `a45a2fb0ccc8594f7ca64f90befdb623ca862c23`
- Candidate app blob: `f49cffd30d252318f4a5cc74a327a45ab64bf9e1`
- Boundary regression blob: `9f7529c549255c8d06498916298acc22c35bfbbb`

Publication uses fresh-main collision checks, atomic Git Data, unique branch/PR, exact diff inspection, `expected_head_sha`, and current-main readback. No force-push.
