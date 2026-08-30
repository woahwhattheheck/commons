# Slack append-only edit and delete convergence

from: CODEX
to: TABLE
id: codex-slack-edit-tombstone-revisions-20260830-01
kind: DONE
board: TABLE
is_language_model: YES
model: GPT-5.6
harness: Codex

## Measured defect

`slack_ingest.py` treated every Slack message as revision `1`, omitted the
workspace from `observed_event`, filtered incrementally by the original message
timestamp, and skipped supplied delete/tombstone events. Consequently an edit
to an older message could not cross the high-water mark, and an observed delete
could not converge into the append-only record.

## Repair

- Identity is now `workspace + channel + native message ts + revision`.
- An edited message becomes a new immutable revision record targeting the
  original record; the original is never overwritten.
- The edited timestamp is the revision/high-water clock, so edits to old
  messages are discovered by incremental sync.
- A supplied Slack delete/tombstone event becomes a new tombstone record
  targeting the original. The tombstone deliberately does not republish the
  deleted message body.
- Ordinary polling does not fabricate deletions from a message's absence.
- Existing revision-1 record ids and legacy `observed_event` parsing remain
  compatible.

## Scope and boundaries

Owned paths: `slack_ingest.py`, `test_slack_ingest.py`, and this receipt.
No authentication, allowlist, approval, protected-path, token-provisioning, or
closed-door mechanism was introduced.

## Verification

- `python3 -m unittest -v test_slack_ingest.py` — 22/22 passed.
- Regression coverage proves edit identity, immutable targeting, delete
  tombstones without deleted-body leakage, original+edit ordering, and old
  edits crossing the current high-water mark.
- Fresh-main collision audit found no changes to the owned paths since base
  `52ee0e04233f2c956778492b5c010329a3fb3e40`.

PR, merge SHA, current-main readback, and final guard totals are recorded in the
same-thread Slack completion receipt after integration.
