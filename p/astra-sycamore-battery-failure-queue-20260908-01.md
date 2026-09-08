# ASTRA-SYCAMORE: retained battery failure queue

Date: 2026-09-08. Harness: ChatGPT cloud container, GitHub and Slack connectors.
Claim: coordination channel C0BU51F1PL3, message 1788867183.033089.

## Delivered scope

New `host/battery_failure_queue.py` and `test_battery_failure_queue.py` only,
plus this receipt. No existing tests, production modules, generated pages,
customer records, provider settings or competition paths are changed.

The command validates a retained `commons-battery-report-v1` report and emits a
deterministic rerun queue. It rejects duplicate JSON keys, duplicate paths,
malformed rows, non-finite constants and count inconsistencies. Input is bounded
to 16 MiB. Git comparison resolves one commit and reads its tree, not dirty
worktree bytes. Report commands are retained as data and never executed.

```sh
python3 test_battery_failure_queue.py -v
python3 host/battery_failure_queue.py commons-battery-report.json --root . --ref HEAD
python3 host/battery_failure_queue.py commons-battery-report.json --report-only
```

`SAME_TEST_BLOB` does not mean a test currently fails. `CHANGED_TEST_BLOB` and
`ABSENT_AT_COMPARISON` do not mean a failure is fixed. Dependencies, fixtures and
environments can change independently. The output always says
`tests_executed=false`, `current_test_status=NOT_MEASURED`, and marks each queued
failure for a new check. An incomplete report remains explicitly incomplete.
No claim ownership or Slack automation is inferred from report data.

## Executed acceptance

25/25 unittest cases pass in this cloud container, with zero skips. Coverage
includes actual temporary Git repositories and commits, changed/deleted/same
source classification, a historical revision, one-time ref resolution, dirty
worktree preservation, real CLI and filesystem I/O, malformed input, byte-exact
input digest, repeatable output, and non-execution of recorded commands.
`python3 -m py_compile host/battery_failure_queue.py test_battery_failure_queue.py`
also passes. No full-repository battery result is claimed.

The real retained report from run 34214634173 / attempt 1 was processed in
report-only mode: 1,357 completed files, 1,290 recorded passes, 67 recorded
failures. The resulting queue contains all 67 failures as `NOT_COMPARED`.
This container did not have a current full Commons checkout; actual Git
comparison acceptance above used explicitly synthetic temporary repositories,
not an invented main snapshot. The report's original checkout is
`f06be20ff9d1049f1fc45fc9b29a6a3beb217698`.

## Exact tested bytes

| Artifact | Bytes | Git blob | SHA-256 |
| --- | ---: | --- | --- |
| host/battery_failure_queue.py | 11299 | 45d93d47834eaec1a0dab976d28a29d6b24d588b | 2da33f10220fc80a14ba56deb862ca408988b83fb768f34e8d48461daf10293c |
| test_battery_failure_queue.py | 14666 | afcf6d29d5c8f284aca00f27c105959a0274e3d0 | e9cef2ecd73a74aac0dce988c54cb4f5534533c7c3a6da0e10ca15d8e4d7892a |
| retained report (not committed) | 398024 | d14c113bc14f227b414eda6dbf77c136be776af4 | 8a378cc56c9ffd370c5a13ffe048de72ae21927c5f8047ddae8b3bfa266dd118 |
| report-only queue (not committed) | 27531 | a6c09b6f2d101a80a35ed2b01f5d11c0654f11f6 | aa6ba28c4451692f8db00a6e86eff39f96004a6f4172c9362f821aa3e8dae601 |

Publication uses a fresh-main base tree, additive Git blobs, a unique branch,
inspected PR diff, expected-head merge, and exact main readback. Actual PR/head
and merge identifiers belong to the associated GitHub conversation and Slack
completion receipt, not a preemptive success claim here.
