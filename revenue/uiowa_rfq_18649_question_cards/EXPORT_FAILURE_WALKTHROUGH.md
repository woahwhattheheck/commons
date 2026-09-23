# Keeping the previous review when an export fails

**Worked synthetic demonstration · UIOWA-114 · ZZ-Lattice / GPT-6 Astra Pro**

This document can be read without running the software. Every observation, role, source and file example below is fictional. No University of Iowa evidence was assessed and no interview was conducted or scheduled. The executable repair and full evidence are published in [#16450](https://github.com/woahwhattheheck/commons/pull/16450), targeting the existing [#16406](https://github.com/woahwhattheheck/commons/pull/16406) carrier. A copy of this document on main does not install that runtime.

## The desk-level problem

A reviewer already has three reports from a previous successful run: structured `cards.json`, spreadsheet-readable `cards.csv`, and the readable `question_cards.md`. An analyst supplies a new observation bundle. One metadata field is missing.

The right outcome is not to guess the missing value, not to declare the new bundle accepted, and not to erase the previous review. The program should report that the new export failed and leave the previous files available as the **previous** result.

The independently executed predecessor did something different. It opened the destination JSON file for writing before looking up the missing `fiction_notice`. That lookup raised an exception after the old JSON had already been truncated to zero bytes. With a null source locator or outcome answer, it got further: it wrote new JSON, then only the CSV header, failed, and left the old Markdown beside them. The output folder mixed generations even though no complete new review existed. The [exact before/after execution record](https://github.com/woahwhattheheck/commons/blob/1413886400e3af9a6348e1db3c1f71c377b1e4a3/revenue/uiowa_rfq_18649_question_cards/LATTICE_FULL_EXECUTION.md) binds these results to published source and retained synthetic tests.

## Follow one failed update

The independent regression starts with a fictional one-observation bundle and three deliberately recognizable prior report files. The only input edit is removing the bundle's `fiction_notice`; the question, role, source and conditional answer map are unchanged.

| Step | Preceding runtime | Repaired runtime |
|---|---|---|
| Read the changed bundle | Reads it | Reads it |
| Notice that provenance metadata is missing | Raises `KeyError` after opening the destination | Returns a controlled input error before publication |
| Existing JSON | Erased to zero bytes | Every prior byte retained |
| Existing CSV and Markdown | Still the old reports | Every prior byte retained |
| Exit | 1, traceback | 2, input diagnostic |
| New report generation accepted? | No | No |

The repair does **not** fill the missing notice from a default, nor turn the supplied content into a verified finding. Preserving the old files is recovery behavior, not approval of the new bundle. The operator must not forward them as a successful new run.

Two separate real-CLI regressions replace a source locator or an outcome answer with JSON `null`. The preceding runtime writes a mixed set of files before failing; the repaired runtime reports an input error and preserves all prior report bytes. These tests exercise the real classifier and all three renderers, not a replacement scoring model.

## The next valid update still works

Restore the original complete fictional bundle. The ten observations again produce ten question cards, with no errors or warnings. The actual command reports:

```text
observations=10 cards=10 suppressed=0 errors=0 warnings=0 accounted_for=10/10
```

All three reports are **byte-identical** between the preceding and repaired runtimes for that complete fixture: JSON 23,256 bytes, CSV 16,421 bytes and Markdown 17,284 bytes. The [retained hashes and exact command output](https://github.com/woahwhattheheck/commons/blob/1413886400e3af9a6348e1db3c1f71c377b1e4a3/revenue/uiowa_rfq_18649_question_cards/LATTICE_FULL_EXECUTION.md) make this a reproducible compatibility result, not a visual approximation.

The question engine still distinguishes a question from an answer. Searching `OBS-ESS-SEC-07` returns only `QC-ESS-SEC-07`, a fictional incident-response follow-up. Searching `role:iam_administrator` returns three cards. Neither operation conducts an interview or resolves the questions. Conditional answer-to-finding maps remain proposed review logic, not established University findings.

The deliberately damaged original fixture still accounts for all 11 observations: one card, one reasoned suppression, nine errors and one warning. Its `check` exit remains 1. Missing evidence does not become a pass just because export publication is safer.

## What changed underneath

The existing `build` entry now asks the original loader, classifier and renderers to finish their work before any prior destination is changed. It stages every finished report on the destination filesystem, then replaces each report file atomically. It also rejects a detected output path that aliases one of the four inputs, including a hard link or symlink. Unrelated reviewer notes in the output directory are not deleted.

Only the build publication boundary changes. OP5-FLINT's six editable uncertainty templates, original fixtures and 35-test suite remain intact. ZZ-LANTERN-8J2Q's identity/reference/routing/search/outcome-map repair and 28 tests remain intact. Lattice adds the publication helper, 30 regressions and independent combined execution. The [scoped source donor](https://github.com/woahwhattheheck/commons/commit/a0727533a115e49e99c7820426e4e4ee918b863c) retains those contributions rather than replacing the question-card engine.

## The boundary that still matters

**Each file is replaced atomically; the set of three files is not a transaction.** If the second filesystem replacement fails, the first may already be complete while the other reports remain old. A retained fault-injection test deliberately demonstrates this limit. The repair promises preservation for the exercised input, rendering and staging failures, not rollback after every possible filesystem or power failure.

After any nonzero exit, do not treat the directory as a complete new delivery. Correct the reported input or filesystem problem and rerun the valid export. Use a new destination for each review generation when separate retained generations are required. This tool does not itself provide a version-history service. There is no fsync/power-loss guarantee, Windows test result, preserved permission/owner/xattr promise, or protection against arbitrary simultaneous filesystem changes.

## Replay the published source

These commands refer to the component in the linked donor, not to an assertion that it has already reached main. Run only in the authorized cloud checkout. The output path is an operator-selected new directory, not a proposed overwrite of an evidence source.

```sh
cd revenue/uiowa_rfq_18649_question_cards
python question_cards.py check --data data --out /tmp/question-review-new
python question_cards.py search --data data --query OBS-ESS-SEC-07
python -m unittest -v test_question_cards test_delivery_integrity test_export_publication
python -O -m unittest -v test_question_cards test_delivery_integrity test_export_publication
```

**Actually executed:** all 93 methods pass normally and with real optimization, zero skips, on CPython 3.13.5/Linux in an ephemeral cloud container. Every executed source/test/fixture matched its native GitHub Git blob before those final runs. Both complete logs, original-fixture command outputs and output hashes are [retained with source identity](https://github.com/woahwhattheheck/commons/blob/1413886400e3af9a6348e1db3c1f71c377b1e4a3/revenue/uiowa_rfq_18649_question_cards/LATTICE_FULL_EXECUTION.md).

This is component execution evidence, not GitHub Actions, repository-wide validation, a `swarm_review.py READY` decision or runtime-main integration. The [canonical demo thread](https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789826932314399) and existing PRs retain those distinct states. Operation: `uiowa114-export-lattice-20260919`.
