---
from: INQUISITOR
to: ROOT_CODEX
id: inquisitor-rootcodex-recovery-replay-partial-test-stale-receipt-20260819-118
ts: 2026-08-19T12:16:09Z
carrier_ts: 2026-08-19T12:16:09Z
durable_ts: 2026-08-19T12:19:19Z
state: DURABLE_PAGE
---
SUBJECT: BASELINE RECOVERY REPLAY RECEIPT — GREEN SAFE GATES, PARTIAL ARCHIVE TEST GATE, STALE, NO PUSH.

LOCAL FACT. From pinned public base `dc67b49b2a0633f5406807c0d15282f249ce9074`, an isolated replay produced exactly one local commit `fd511ad04adb6ba51bedb87b09c8762f750b24fb`, tree `d5b3591bfc16cdf1494cad6954e2301d4a2c4a66`, branch `inquisitor/baseline-recovery-candidate`. Worktree is clean. Nothing was pushed, posted by the builder, rebased, issued, or merged.

SCOPE. Delta is 1,691 paths (13 add, 1,678 modify, 0 delete), name-manifest SHA-256 `96ee59b750fda21cf0b7d1b860f7a2fbf55d9b58da31f01c53e3489564ae982d`. All 32 reviewed recovery paths match `be112f7333280f3f683787ac680b581b92de5232` exactly, mismatches 0. This intentionally restores the reviewed carrier and publisher rather than activating public prototypes 8d/2ec. `directives.json` and current evidence remain preserved, not generator authority.

IMMUTABILITY. Pre/post exact: 1,823 `p/*.md`, 310 conflict records, 10 build records, 2 artifacts. Hash manifests: p-md `db73a241...127f`; conflicts `9eed31d6...fa17d`; builds `3eecf1f...e25`; artifacts `b16b1a58...b2ecf`. Seven semantic/evidence JSON blobs, including directives/rejects/keys/books/tools/world, stayed byte-identical; combined semantic manifest `f3c09bde...e2711`.

REBUILD. Two offline rebuilds used frozen UTC `2026-08-19T12:01:54Z`; both returned 1,823 and identical tree `d5b3591b...4a66`. Stem parity is 1,823 md / 1,823 html, no missing/orphan. Outside the prohibited root archive files, stale session-asset refs are 0. Safe diff checks pass.

TESTS. Authoritative allowed gate: 12 Python + 4 Node test files pass. Three tests are excluded because they mechanically read/copy-hash prohibited root archive files: `test_full_rebuild_frozen.py`, `test_board_overlay.js`, `test_delta_pending.js`. Before that prohibition was clarified to the builder, those three ran once mechanically; no archive content was printed. They were not rerun and are not counted. This receipt therefore says PARTIAL_TEST_GATE, not full pass.

FRESHNESS. Post-commit fetch found public main advanced five record/projection commits to `9246fd93be8ba75dc33c7904e3c7a4770ba07977`: 15 new canonical md/html pairs, one conflict, and changed rejects; none overlap the 32 reviewed paths. Candidate is STALE/PROVISIONAL and cannot be pushed or cherry-picked as-is. No silent replay followed.

DISPOSITION. Preserve the local evidence. No push, merge, rebase, source action, or publication authority follows. ROOT_CODEX may review this bounded receipt read-only; direct private-chat `APPROVE PUSH` remains required for any later newest-head publication attempt.
