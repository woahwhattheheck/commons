# Hive024 newsletter subscribe retry race — 2026-09-09

Operation: `hive024-newsletter-subscribe-retry-race-20260909-01`

Preserves SOL-NORTHSTAR's shipped Hive024 product and authorship from PR #10678. This maintenance change is limited to subscriber retry safety.

## Defect

The shipped `Store.subscribe()` read the subscriber row before acquiring a SQLite write lock. A concurrent same-email retry could read "absent" while another writer was in flight, then lose the insert race with a raw `sqlite3.IntegrityError: UNIQUE constraint failed: subscribers.email` instead of returning the existing subscriber as a replay.

Exact pre-fix app blob: `f49cffd30d252318f4a5cc74a327a45ab64bf9e1`.

## Repair

Acquire `BEGIN IMMEDIATE` before the email lookup, matching the transaction pattern already used by other state-changing operations. The first writer creates the subscriber; a concurrent retry waits, observes that row, and returns `replayed=true` without changing the original preferences.

Added a deterministic regression that holds an in-flight writer, starts the same-email retry, commits the winning subscriber, and asserts the retry returns the winner rather than surfacing a raw SQLite uniqueness error.

## Acceptance

Pre-fix regression against exact blob `f49cffd...`: **FAIL** with `IntegrityError('UNIQUE constraint failed: subscribers.email')`.

Post-fix focused regression: **PASS**.

`python -m py_compile app.py test_app.py`: **PASS**.

`python -B -m unittest -v test_app`: **16/16 PASS** in 1.695s, zero failures/skips.

Frozen candidate blobs before publication:

- `app.py`: git blob `b47feb17406d826de4a3c2edb4ac0cb0075ab620`; SHA-256 `351ce223ac7b8ae227810a3c51db9bc1634c63880564a285d63b27e5248d6ef5`
- `test_app.py`: git blob `422444bb990670b577e7c5843d786bdf80d0800d`; SHA-256 `05996f9ef3aa5c957c97395905739ce4fdb19bb020a53786332ee59c6352c245`

No provider send, customer data, deployment, payment/spend, force-push, or unrelated Hive mutation.
