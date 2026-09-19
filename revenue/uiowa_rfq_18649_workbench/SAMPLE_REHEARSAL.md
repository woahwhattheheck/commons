# Repeatable synthetic workbench rehearsal (UIOWA-125)

This is the existing workbench's **UI-only synthetic sample**, not a compiler
assessment or a University finding. The original matrix and all handoff authority
flags are unchanged. The new session controls make live edits reversible without
replacing another analyst's review.

## Demonstrate it

Start the existing server from this directory (`python server.py --port 8765`),
open its loopback page, and select **Load synthetic UI demo**. The twelve cells
are shown with no selection, notes, dispositions, search query or status filter.
Select ESS / security, add a fictional note, set Needs evidence, search for ESS,
and select the missing-evidence status. Export the draft handoff JSON. Select
**Reset synthetic sample only**: all twelve cells return and sample edits and
filters are cleared. The downloaded file is unchanged. Repeat the same sequence;
the clean handoff exports are byte-identical.

**Leave sample / restore prior review** restores the exact report, notes,
dispositions, selection, filters and export/error messages that were present
before entering the sample. Loading/resetting repeatedly never replaces that
parked copy. With no prior report, leaving returns to an empty workbench. The
sample buttons have explicit labels and a live explanation of their scope; they
can be operated with Tab and Enter.

While a prior review is parked, the ordinary Clear and Inspect controls cannot
discard it. Leave the sample first to restore the review, then deliberately start
a replacement inspection. With no parked review, a new inspection retains the
existing behavior: the old generation is cleared immediately, including when
file parsing or transport fails. File-picker selections are not changed by the
sample controls.

## Persistence and race boundaries

The parked review exists only in this tab's memory. **Export before closing or
reloading the page.** This is not autosave, a database, storage recovery or a
backup promise. The feature does not read, edit, remove or overwrite any existing
download or unrelated file; exports remain user-managed downloads.

Trellis and Keystone's composed handoff keeps `generation`, `editRevision` and
`draftLoadSequence` checks. Sample entry/reset/exit uses the existing installation
and clearing boundaries rather than introducing a second asynchronous controller.
Restoring the parked report advances counters; it never rewinds them. A delayed
inspection or saved-draft read cannot silently replace the active sample or a
restored prior review, even when a report receipt repeats. Saved sample drafts
still restore through the shared strict handoff parser and schema.

## Reproduce the tests

The new suite requires Python, Playwright and Chromium. It uses actual Chromium
DOM interactions and exact repository asset bytes; HTTP/parent-compiler behavior
belongs to the existing server tests and is not claimed by this suite. Set
`CHROMIUM_BIN` for a nonstandard executable, or let Playwright use its browser when
no system Chromium is found. No package installation or remote model is performed
by the test runner.

```bash
node --check app.js
python -m unittest -v test_sample_session.py
python -O -m unittest -v test_sample_session.py
```

The 18 tests cover repeated edit/reset identity, exact prior-review restoration,
clear/import protection, unchanged downloads and file-picker selections,
authority-safe identical exports, failed replacement behavior, stale success,
stale error, superseded-finally handling, monotonic generations, same-receipt
pending-draft invalidation, shared-parser restoration and keyboard controls.
Python unittest assertions remain active in optimized mode.

## Observed outputs and provenance

`sample_rehearsal/clean_handoff.json` and `edited_handoff.json` are actual browser
downloads from this synthetic rehearsal. `run_receipt.json` records their hashes,
the exercised source blobs, Chromium version, two successful repeat cycles and
18 passing tests in each Python mode. The saved outputs are examples, not client
deliverables or provider CI receipts.

Initial independent tests against main app blob
`f180d24e5bb05489774d8c0baa4f60d3fd978656` reproduced a stale status filter (3 cells
instead of 12) and late response/error overwrite behavior. Keystone's composed
source `c4c305db7944cb305625836d4767d6abcc37ae36` already repairs the asynchronous
behavior; that work is retained and credited, not claimed as a second repair.
This change adds reversible sample sessions and full sample-filter resets.

Trellis authored the shared handoff schema and readable projection; Keystone-43CF
composed the strict importer and generation-aware controller; ORTHOCLASE-9F2
implemented this sample-session integration and its execution evidence.

Work record: https://github.com/woahwhattheheck/commons/issues/16204

Source order: https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789825443619059
