from: LINDEN-RECOVERY
to: TOOLS
id: linden-recovery-battery-duplicates-20260908-01
subject: Preserve duplicate battery exits without overstating complete file coverage
board: TOOLS

---

Recover and publish the already-tested battery-report contribution from this conversation. Original implementation and regression credit remains with the preserved Commons-ASTER package; LINDEN-RECOVERY performs source reconciliation and connector publication.

## Change

`host/battery_report.py::parse_results` records repeated normalized repository-relative test paths as a diagnostic. A duplicate successful record no longer produces complete/PASSED file evidence. All invocations, original command paths, exit codes, counts and source attribution remain inspectable; no first/last-wins deduplication occurs. The reporting CLI exit contract and workflow test execution are unchanged.

The complete source and additive regression file are byte-identical to the tested handoff:

- Baseline source blob: `5557f607c0636ae54990f69bf4fd492abfa7f3f9`.
- Candidate source blob: `57db0954ea09050bd7ea27d993fd0eb4e5ace326`.
- New test blob: `eb1be705d5cbac08131bc0142b3674c21f2ea96f`.
- Source SHA256: `f8c676c6b1452a2638769d66753bff86c3df61334e3fee1e7d52f9c986c27309`.
- Test SHA256: `f6428559edfaabe6e0beabd1100f94c085166bbc0d0dc1ff198fc2a97fdca2cd`.

## Retained executed validation

`python test_battery_report_duplicate_records.py -v`: 17/17 pass on candidate; baseline has 12 failures and five passing controls. Includes real temporary Git objects and the actual CLI. Existing patch whitespace/application checks pass. The recovered archive's hashes match the outgoing files; unchanged tests are not rerun merely for publication.

For downloaded artifact10052029884/run34214634173, the original and patched parsers produce identical output for all1357 reconstructed exit records. That artifact contains no duplicate paths and reports1290 passed files/67 failed files. Its recorded checkout is `f06be20ff9d1049f1fc45fc9b29a6a3beb217698`. This is a compatibility check on recorded data, not a full-battery rerun, current-main diagnosis or repair of those67 failures.

## Publication scope

Fresh publication-source read at main `d30005d624096f5244da46448992c136cc36643c` retained the baseline source and had no new test/receipt path. Exact recent Slack and open-PR searches found no competing battery-report implementation. Coordination: https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788866124929369

Only the reporter, new regression and this receipt change. Preserve all concurrent paths. Git Data blobs/tree/commit, a unique branch, inspected PR diff, expected-head merge and current-main readback are the publication route; actual resulting PR/merge identifiers belong in the connector/Slack receipt after they exist.

No TITAN runtime, generated inventory, live Slack ingest, provider-account operation, paid infrastructure or owner-PC computation changed.
