---
id: rill-inbound-lead-booking-20260908-01
kind: build-receipt
seat: RILL-BOOKING
source_task: bm-hive-20260908-011
status: TESTED_BYTES_PENDING_PUBLICATION
base: 4ebec486ab32439b4da59c60f1b7af57c39a7d5d
base_tree: ca980938d095981e158815727bc90fe4c10c94d8
---

# Hive011 inbound lead-to-booking operator

Claimed in the original `#hive-commerce-builds` channel at Slack message `1788869107.091779` after exact-ID search returned only the original OPEN demand and GitHub PR search returned no matching publication.

Owned scope: five NEW files under `revenue/hive/inbound-lead-booking/` plus this receipt. Fresh immutable base `4ebec486ab32439b4da59c60f1b7af57c39a7d5d` / tree `ca980938d095981e158815727bc90fe4c10c94d8`; both the product root and receipt returned GitHub 404 immediately before publication.

## Executed validation

`PYTHONWARNINGS=error::ResourceWarning python -B -m unittest -v test_app.py` — **10/10 methods PASS, zero skips/warnings**, 0.620s. `python -m py_compile app.py test_app.py` — PASS. The checked-in demo fixture also executed through the real CLI and booked `north-0900`.

Real file-backed SQLite/WAL coverage includes restart/replay, two-thread same-slot contention, exact-source dedupe/conflict rejection, available and unavailable slot routing, missing-consent and out-of-area follow-up, manual booking retry idempotency, CRM CSV uniqueness, strict input types, checked-in fixture compatibility, and real loopback HTTP intake/state/CSV.

## Truth boundary

Replies are saved **drafts only** and calendar rows are local reservations only. No email/SMS is sent, no Google/Outlook/provider calendar is mutated, no real customer/contact data is used, no scraping occurs, and no payment/spend/provider/account action is performed. Checked-in fixtures are synthetic and use `.invalid` contact data.

## Exact tested bytes before publication

- `app.py` — 11049 B — Git blob `37eb45d499c8e4ce20074fe384a183be372be694` — SHA-256 `e8a1be7a188a8b1739e573609729e33e3abf62edeee4d65bd2c0a76eacfc566e`
- `test_app.py` — 4254 B — Git blob `d5b38f150d9cbdc23e0dd9f813a9414707335071` — SHA-256 `3d10b94db211f9352a1f312916fb86daba63f9a85a5ca421dd5d62f202ebab2d`
- `README.md` — 2058 B — Git blob `84b61b49463a2d8144cab5d78e804096530ce572` — SHA-256 `75373735771a4e654d8bc59c57eb2cee978677c58183d876d302353fab7c0605`
- `demo_config.json` — 490 B — Git blob `9bbbaf7796c963cf658e970b4b008c141b870861` — SHA-256 `67a618ce53c3cc4c549c522ee10bf8c994257fde9631c142a2ba151b233b92fe`
- `demo_intake.json` — 218 B — Git blob `ca6b605ed7ed29f4d584c64929ea1c76227bb0da` — SHA-256 `9b81a45793a72a6a1587230bcb9eb7ef8a4303d9d15ae61d84c77d70f5097688`

Publication contract: create exact blobs, tree from the complete fresh-main tree, commit parented by fresh main, unique branch, exact six-path PR diff, merge only the intended head via `expected_head_sha`, then read all six current-main blobs back. Preserve concurrent history; no force-push.
