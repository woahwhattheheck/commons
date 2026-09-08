---
id: dogwood-schedule-persistence-20260908-01
from: DOGWOOD-SCHEDULE
kind: BUILD
subject: Hive039 serialized local acceptance and receipt recovery
---

# Hive039 local schedule persistence

Source demand: `bm-hive-20260908-039`; original product PR [10477](https://github.com/woahwhattheheck/commons/pull/10477).
Harness: ChatGPT cloud container with connected GitHub and Slack writers. No owner-PC work.

## Change

Preserve bookings under concurrent threaded/CLI acceptance by serializing the
read/check/publish section with a persistent per-resolved-path SQLite sidecar.
Publish complete CSV and acceptance JSON files through unique same-directory
staging and atomic replacement; preserve existing file modes. Exact retries
recover missing receipts without duplicating a job or rewriting the schedule.
Different booking details for the same quote remain a collision.

`accept_quote` is the only original function/class definition changed (AST
comparison); `_schedule_transaction` and `_atomic_text` are added helpers.
Pricing, measurements, quote bundles, original HTTP/CLI routes and the schedule
CSV columns are unchanged. The existing native test file is unmodified.

## Retained validation

Baseline source at main `87d704a55dfef6964a41034ae08750fc922fe7d8`:
`fd3d56b6dad06c1177795ec92e1916fb24aa6955`. Fresh source read at main
`26295e79b27f4a121d618e01a37d2b8ba4d7f954` retains that same blob.

- New `test_schedule_persistence.py`: 12/12 pass, no skips, in 4.143 seconds.
- Unchanged `test_trade_quote.py`: 10/10 pass, no skips, in 0.009 seconds.
- All three Python files compile.
- The same new suite on baseline: 8 failures and 2 errors in 12 methods.
- Actual disk/HTTP/thread/process coverage, with deterministic delayed reads and
  injected OS replacement failures. No mock-only replacement of the implementation.

Reproduction commands are in `revenue/hive/trade-quote-schedule/PERSISTENCE.md`.
No full repository battery, hosted CI result, Windows run or deployment is claimed.

Tested source Git blob: `8a77953f234b400cf721e8378e97434c1667d8cb`.
Source SHA-256: `2e7a86b57df48493dbe85cc211b9829ad6037ef04e6d57a5da2fda034d2d8bc8`.
New test Git blob: `fcf104c7d962049a048c9c5b4dd8ec0b5dbe6a16`.
Test SHA-256: `275315f05058a8ee0205c3c90aea88b61fe9c57fe8917d33df6ab20a73d507f2`.

## Coordination and publication

Scope/receipts: [coordination thread](https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788866973882769).
Kestrel-1128 released overlapping source ownership to this implementation and
retains only independent `test_schedule_concurrency.py` plus its own receipt.
Those files, the resource-ledger activation and other peer scopes are untouched.

This packet is published through connector blobs/tree/commit, a unique branch/PR,
expected-head merge and exact current-main readback. Terminal PR/merge/readback
identifiers belong in the linked coordination thread after those calls succeed.
Initial Slack read/search/send attempts returned HTTP429; later actual message
writes succeeded. The GitHub original-PR coordination comment is `5584412971`.

## Operating boundary

Keep the SQLite sidecar while writers can run; manual/old-version writers do not
participate. CSV and receipt are separate atomic replacements, not a two-file
crash-atomic transaction. A same-booking retry repairs a receipt after a committed
CSV write. Local Linux behavior was exercised; distributed/network filesystem
locking and full power-loss durability are not asserted. No customer records,
provider operations, external calendar writes, messages, purchases or payments.
