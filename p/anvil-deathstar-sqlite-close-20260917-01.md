# anvil-deathstar-sqlite-close-20260917-01

Seat: ANVIL (Devin Desktop / SWE-2 peer)
Task: anvil-deathstar-sqlite-close-20260917-01 (follow-on to anvil-deathstar-binary-io-20260917-01)
Repo: woahwhattheheck/deathstar
PR: https://github.com/woahwhattheheck/deathstar/pull/140 — MERGED, squash 4ffa0bb3e378e72b2092878dcdfe56ad6c971888

## Fix
`with sqlite3.connect(...)` commits/rolls back but does NOT close the
connection — leaked handles kept `handoff_mailbox.sqlite3` /
`worker_presence.sqlite3` locked on Windows so tearDown rmtree failed
(WinError 32). Wrapped the four fixture sites in `contextlib.closing`,
keeping inner `with db:` commit semantics for writes.

Files: tests/test_handoff_mailbox.py, test_handoff_mailbox_snapshot_atomicity.py (x2), test_presence.py.

## Evidence
47/47 green in the three touched files on Windows; prior 4 teardown errors eliminated.
Tip KEEP · Still GO.
