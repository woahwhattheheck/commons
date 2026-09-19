# One-command synthetic workbench replay

Run from `revenue/uiowa_rfq_18649_workbench`:

```bash
python replay_sample_session.py --out /path/to/new-rehearsal
```

The output's parent must already exist. Any existing output path, including a symbolic link, is refused without touching its contents. Use a fresh directory for another run. Nothing is installed, recursively deleted, or overwritten. Playwright and Chromium must already be available; `CHROMIUM_BIN` selects a nonstandard browser executable.

The runner executes the full 18-case sample-session Chromium suite in normal and optimized Python. It then performs two real edit/export/reset cycles, verifies identical clean handoffs and an unchanged edited download, captures the current workbench screenshot, and verifies that leaving the sample returns to empty state when no prior review was parked.

It retains `normal-tests.txt`, `optimized-tests.txt`, `clean_handoff.json`, `edited_handoff.json`, `sample-reset.png`, and `run_receipt.json`. The receipt records observed subprocess counts and Python modes, browser version, source hashes before and after execution, output hashes, and the demonstration's observed checks. Counts are not copied from a stored PASS claim. Failed, empty, skipped, expected-failure, malformed, or nonzero-exit test runs cannot produce a PASS receipt; source drift also prevents PASS. Execution failures retain failure information rather than deleting their output directory.

Runner-boundary regressions are separate from the 18 browser cases:

```bash
python -m unittest -v test_replay_sample_session.py
python -O -m unittest -v test_replay_sample_session.py
```

These 12 tests exercise observed-count preservation, nonzero exit, missing/ambiguous records, invalid counts and modes, failed/skipped suites, refusal of existing directories/files/symlinks, no recursive parent creation, no file replacement, failure-only output, and source-drift rejection.

## What the evidence does and does not establish

This is actual Chromium running the checked-in application bytes with fictional sample data. Network responses in the transport regressions are synthetic. This runner does not execute the server or parent compiler, make a University assessment, create approval authority, install dependencies, invoke a model, or schedule anything.

The workbench still parks prior work only in tab memory. Export before closing or reloading the page. Downloaded handoffs are user-managed files and are not edited or deleted by sample resets.

Local execution is not GitHub Actions execution authority. The repository's exact-current-main provider checks and final main readback remain separate integration requirements.

Implementation and coordination: https://github.com/woahwhattheheck/commons/pull/16275 and https://github.com/woahwhattheheck/commons/issues/16204 .
