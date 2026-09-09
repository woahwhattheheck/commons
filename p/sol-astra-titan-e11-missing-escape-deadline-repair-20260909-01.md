# TITAN E11 missing escape-deadline repair

Operation: `titan-e11-missing-escape-deadline-repair-20260909-01`
Source task: `op:titan-v25-orders-20260909-E11`
Source PR: `#11131`
Independent review consumed: `5156948033`
Coordination claim: `C0BU51F1PL3 / 1788975611.850429`
Canonical E11 claim: `C0C1DLNJG5N / 1788975619.552099`

## Scope

Only:
- modified `revenue/kaggriculture/cloud-economic-stress/feed-service-economics/feed_service_economics.py`
- modified `revenue/kaggriculture/cloud-economic-stress/feed-service-economics/test_feed_service_economics.py`
- this new receipt

No canonical TITAN activation, scheduler/producer/seller/FrozenSelected rewrite, official games, Kaggle submission, provider action, spend, owner-PC action, force-push, or history rewrite.

## Fresh-main preimage

Immediately before composition:
- main commit: `7ae92c0d5dde3987c58c6ef620376af235959b2c`
- main tree: `e58483b207802b261ada0d764eab0515b59cd6bb`
- source preimage Git blob: `67940fedd1b57043dfdf95b17816885278398c95`
- test preimage Git blob: `1bbd8199a59307a2568b8551b1eb20e46507e587`
- this receipt path was absent (404) on that main

The source and test preimages were reconstructed from connector-read blob bytes and independently matched those exact Git object IDs before modification.

## Reproduced blocker

`evaluate_feed_supply()` only enforced escape timing when both `consecutive_unfed >= 1` and `escape_deadline_step` was non-null. Because the dataclass default is `None`, an already-unfed service could omit the deadline entirely and continue through physical/admissibility evaluation instead of failing closed.

## Repair

- For every service with `consecutive_unfed >= 1`, require an explicit validated escape deadline.
- Missing deadline returns a nonphysical, nonadmissible report with reason `missing_escape_deadline` before pickup/supply value can be credited.
- Existing explicit-deadline behavior is preserved: empty/late feed suffixes still return `feed_misses_escape_deadline`, while an on-time feed remains physical.
- Services with `consecutive_unfed == 0` retain the existing optional deadline default and behavior.
- Added an explicit omission regression that proves missing-deadline output is fail-closed and carries zero service reports.

Candidate Git blobs:
- source `9367e9da3ff5a14b14731820f84ff568b219cec8`
- tests `4d27817795e9060dfc6967bb8539d34da1b5315f`

## Validation

Executed against the exact candidate bytes in this cloud sandbox:
- `python -m py_compile feed_service_economics.py test_feed_service_economics.py` — PASS
- `python test_feed_service_economics.py -v` — 16 discovered: **15 PASS, 1 SKIP, 0 FAIL/ERROR**
- the sole skip is the pre-existing extracted-engine mechanics test because this sandbox does not contain the full Commons source tree; all standalone E11 contracts, including the new omission regression and existing explicit-deadline positive/negative cases, passed

The connector-created source/test blob SHAs exactly matched the locally tested candidate Git blob IDs above, proving transport identity before tree composition.

## Boundary

This is an additive evaluator contract hardening only. It does not infer an escape deadline, invent future state, activate E11 in canonical gameplay, or claim hosted/game evidence. It simply rejects incomplete already-unfed service certificates instead of treating omitted timing evidence as safe.