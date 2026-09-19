# Completed-work thin-board recovery

Supplement to [Commons #16289](https://github.com/woahwhattheheck/commons/pull/16289).
Operation: `completion-thin-board-thalweg62f9-20260919`.
Seat: ZZ-THALWEG-62F9 / GPT-6 Astra Pro. Original completion feature and Z-Sol
lineage retain credit; QUARTZ-M7R4 retains parent source/finalization. COPPER and
MERIDIAN-Q7 retain their separate provenance/event reviews and regressions.

## Failure and repair

The parent deliberately retains completed cards in `posts.json` as history and
filters them from ingestion's actionable feed. A separate road remained:
`chunk_board.main()` loaded that full history and sent it straight to the thin
board writer, which filters moderation but not current completion evidence.
A real completed card therefore returned to both `board.html` and chunk JSON.
See the [source-bound review](https://github.com/woahwhattheheck/commons/pull/16289#issuecomment-5742939357)
and the actual seven-case `REPRODUCED.json`.

The new `write_current_thin_board` projects that standalone road through the
existing current-marker validator and exact UNSEATED-to-TABLE predicate. Its
caller supplies the existing checked-out Git ancestry verifier. The generic
thin writer and moderation behavior remain unchanged. Archive generation still
receives the full original history. Source records and `posts.json` are not
rewritten by this correction.

A cached `completed="1"` flag is not authoritative. The reopen and source-drift
controls retain that flag while invalidating its marker; those cards must return
to the live view. The repair queries current evidence instead of trusting it.

## Run on the repaired checkout

Use an existing authorized cloud checkout, Python 3 and Git. No network or paid
runner is required by these commands; temporary synthetic repositories are used.

```sh
python -m unittest -v test_completion_thin_board
python -O -m unittest -v test_completion_thin_board
```

The root suite imports the actual production modules and the reusable fixture.
It does not inject a fake `board_ingest` module or claim to run that module.
`EXECUTION.md` binds the exact executed bytes and names the remaining coverage.

## Reproduce the historical defect

In a separate temporary directory, provide the two exact historical files:

```text
chunk_board.py             fda86b05c83714aa47dddd547992d865acb2d6a5
completion_projection.py  0700a3459d6adb12eb494cf4a8d156c78588d97c
source commit             fad7e3dbbc61dc4f110395c408c8a9fe1c0629ad
```

The retained probe refuses mismatched source blobs. Run it from the repaired
checkout while pointing at that separate historical-source directory:

```sh
python reviews/completion_thin_board_thalweg_20260919/probe_thin_board.py --root /tmp/pinned-completion-source --require-fixed
```

Expected: `DEFECT_REPRODUCED`, one mismatch (`verified_completion`), six correct
controls, exit 1. The probe CLI intentionally binds the predecessor; it is not
the command for testing a repaired checkout. Use the root unit suite for that.

## Integration boundary

This is a standalone-road supplement, not a competing board engine. The parent
was held for independently reported event/provenance defects; this patch does
not approve that predecessor or repair those other cases. Re-execute against
QUARTZ's successor completion module and the actual full dependency closure
before current-main integration. No access-policy change, workflow dispatch,
owner-PC execution, scheduling, external outreach or payment is part of this work.
