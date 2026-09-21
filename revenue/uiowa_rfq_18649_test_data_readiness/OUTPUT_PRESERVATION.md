# Test-data reports that preserve their source evidence

UIOWA-047 operator walkthrough and executed output-preservation evidence.
Prepared September 19, 2026 by ZZ-COPPERFIN-Q8D6 / GPT-6 Astra Pro.
All inputs in this demonstration are fictional; no University system or record is inspected.

## The operator problem

A correct assessment is not a safe delivery when saving its report destroys the
catalog it assessed. On the exact predecessor below, the command-line interface
returned success while overwriting a fictional input catalog in three cases:
its output had the same pathname, was a symbolic link to the catalog, or was a
hard link to it. A separate Unicode encoding failure truncated an existing
report before returning a traceback. These observations are retained in
[issue #16408](https://github.com/woahwhattheheck/commons/issues/16408).

The repair extends the existing assessor rather than introducing another
assessment engine. It checks the destination, writes a temporary file beside
it, flushes that complete file, checks the destination again, then replaces only
the distinct report path. A normal replacement of an existing ordinary report
is still supported. Expected output errors return a readable diagnostic and
exit code 2 without publishing a partial report in the exercised scenarios.

The original kit belongs to ZZ-Sol / #16122. R9C4 owns the chronology/coverage
repair and canonical integration on [#16397](https://github.com/woahwhattheheck/commons/pull/16397).
HARBOR-C9V2's independent semantic review remains separately attributed.
Q8D6 contributes file-delivery protection, its tests and this worked rehearsal.

## Source and integration boundary

The complete runtime and regression donor is
[`4a25d53a2a0ae1d6ac9f39bc2b59ce248eb28d1a`](https://github.com/woahwhattheheck/commons/commit/4a25d53a2a0ae1d6ac9f39bc2b59ce248eb28d1a),
on `swarm/uiowa047-output-copperfin-q8d6-20260919`. It directly descends from
R9C4's `650d258693f0d479bf17d12fc0eb2abb31631dd8`; it does not move that shared ref.
The rehearsal and execution archive accompany this guide on the same donor branch.
All paths below are relative to `revenue/uiowa_rfq_18649_test_data_readiness/`.

| Artifact | Exact Git blob | Bytes |
| --- | --- | ---: |
| Predecessor `test_data_assessor.py` at R9C4's head | `9def5e7e260d19d11e5fbb85b41d74a655cefcd7` | 15,678 |
| Repaired `test_data_assessor.py` | `556a10da2af218ca0fc73728bfb8de835b5dc65d` | 17,634 |
| `tests/test_output_preservation.py` | `52554012956501799700e6835d9621f7cf9980ee` | 12,874 |
| `rehearse_output_preservation.py` | `6e2135775490206fb0cb160d501d5fd3252bb4d9` | 7,447 |
| `output_preservation_review/EXECUTION.json.xz` | `acf4fdac4efda47d5e3178b8e800f8613af14bfe` | 5,448 |

Native publication returned the same blob identities as the exercised buffers.
This document can be integrated independently as inert documentation. Its
presence on main does **not** prove the runtime donor, replay executable or
canonical #16397 has passed hosted execution or merged to main. Consult the
canonical PR's actual head, provider results and literal-main source readback
for that separate integration decision.

## Nine real CLI scenarios

Every row ran in a fresh temporary directory, using the same captured assessor
buffer for that version. No checked-in fixture was overwritten. The predecessor
passed its three ordinary-output controls; the repair passed all nine delivery
expectations. This is nine authored scenarios, not a maturity score or a claim
of nine independent defects.

| Scenario | Predecessor observation | Repaired observation | Operator consequence |
| --- | --- | --- | --- |
| New JSON report | Exit 0; catalog retained | Exit 0; saved bytes equal stdout; catalog retained | Normal JSON delivery remains usable. |
| New Markdown report | Exit 0; catalog retained | Exit 0; saved bytes equal stdout; catalog retained | Normal readable delivery remains usable. |
| Replace distinct ordinary report | Exit 0 | Exit 0; complete report replaces prior bytes; mode 0640 retained | Existing replacement workflows remain supported. |
| Output is input pathname | Exit 0; catalog replaced | Exit 2; catalog retained | An accidental same-path save is refused. |
| Output symlink points to input | Exit 0; catalog replaced | Exit 2; catalog and link retained | A second filename cannot silently erase the input. |
| Output hard link points to input | Exit 0; catalog replaced | Exit 2; both names and catalog bytes retained | Identity is checked beyond pathname spelling. |
| Output symlink points to a different prior report | Exit 0; target report replaced | Exit 2; target and link retained | This is an explicit compatibility change: choose a regular output path. |
| Output parent does not exist | Exit 1 with traceback | Exit 2 with an output diagnostic; no report created | The operator sees a delivery error, not a successful assessment save. |
| Markdown contains an unencodable surrogate | Exit 1 with traceback; prior report changed | Exit 2; prior complete report retained | Failed encoding does not destroy the previous delivery. |

For the repaired fixture, the future refresh and cleanup verification remain
`UNKNOWN`, while its explicit empty covered-case list remains `OBSERVED_GAP`
against the recorded requirements. Evaluation and rendering functions are
unchanged by this output-only patch. A successful file save still does not mean
that every assessment check is evidenced.

## Run the demonstration

Use an existing approved cloud checkout containing the donor's source and replay.
From the component directory, run:

```bash
python3 -B rehearse_output_preservation.py --expected-source-blob 556a10da2af218ca0fc73728bfb8de835b5dc65d
python3 -O -B rehearse_output_preservation.py --expected-source-blob 556a10da2af218ca0fc73728bfb8de835b5dc65d
```

The optional pin rejects a different assessor before execution. The replay reads
that source once, copies it into temporary scenario directories, runs actual CLI
subprocesses, reports all nine cases and removes those temporary directories.
It never writes to the assessor supplied by the operator. Each invocation emits
JSON to stdout and returns 0 only when all nine expectations hold. A baseline
contract failure returns 1 while retaining the failed cases in the JSON.

Read `input_preserved`, `assessor_preserved`, `actual_exit` and `passed` for each
case. For applicable rows, read `previous_report_preserved`,
`report_matches_stdout`, `evidence_states_retained` and `existing_mode_retained`.
A null field means that specific comparison does not apply to the row, not that
it passed. The observed repaired summary is `passed: 9`, `total: 9`,
`all_passed: true`. The exact predecessor returns `passed: 3`, `total: 9`,
`all_passed: false`.

Only ephemeral directory and staging basenames are normalized in displayed
error diagnostics. Their meaning, exit status and file comparisons are not
normalized. The final normal and optimized replay JSON is byte-identical,
SHA-256 `c3a229f979a0b5e0e6955d37ce3e811cfda5103fec8b8cc588f83da73c4e41d0`.

## The deeper failure checks

The reusable source-buffer-bound regression suite adds partial staging writes,
stream flush and disk-flush failures, replacement refusal, descriptor-wrapping
failure, staging-creation failure, mode-copy failure, interruption, parent-path
aliases and a destination alias introduced during staging. The latter test
requires retaining the externally introduced hard link, not deleting it.

```bash
python3 -B tests/test_output_preservation.py
python3 -O -B tests/test_output_preservation.py
```

Actual execution on the existing ephemeral Linux cloud environment with CPython
3.13.5: **26/26 normal tests**, 12.674 seconds; **26/26 real optimized tests**,
completed as two disjoint 13-case shards in 23.332 and 15.027 seconds. Every
method appears once across the retained shard list; no test was skipped.
CLI subprocesses inherit the interpreter's actual optimization mode.

The same selected tests against the exact predecessor produce four expected
failures for the three source aliases and the encoding case, while the ordinary
report-replacement control passes: five tests, four failures, exit 1, 4.223
seconds. The complete nine-case CLI replay independently records the actual
catalog/prior-report byte loss, rather than inferring it solely from an exit code.
These results are separate from R9C4's earlier 64-test and HARBOR's 13-test
semantic results; Q8D6 does not relabel those other authors' runs as its own.

## Inspect retained execution records

`output_preservation_review/EXECUTION.json.xz` decompresses to one 51,580-byte
UTF-8 JSON document. It contains four exact source bindings, fourteen named
literal records, test and replay results, source donor, Python/platform details
and limitations. Read it without extracting files:

```bash
python3 -c 'import json,lzma; from pathlib import Path; p=Path("output_preservation_review/EXECUTION.json.xz"); d=json.loads(lzma.decompress(p.read_bytes())); print(d["files"]["NORMAL.log"]); print(d["files"]["OPTIMIZED_1.log"]); print(d["files"]["OPTIMIZED_2.log"])'
```

The archive SHA-256 is
`fbec08ed732760ea34d5746263aa3d4b71dd4b7f5a2dec17c2042c9c1a634ebb`.
Its literal records also include the interrupted optimized log, selected
negative-control log, complete shard names, before/after nine-case outputs,
initial unnormalized replay outputs, four-case baseline probe and source patch.

An initial full optimized test invocation hit the outer timeout; it is not
counted as success. A first optimized replay tool invocation returned a transport
error before any output or running replay was found; the completed retry is
separate. Initial replay outputs passed all behavior checks but differed in a
random staging basename; those observations are retained alongside the final
explicit diagnostic normalization. A preliminary test incorrectly expected a
new external hard link to disappear and was corrected before the accepted run.

## Filesystem and operational limits

This is one-file staged replacement, not a multi-file transaction, backup system
or power-loss durability guarantee. The directory itself is not fsynced. Keep
independent backups when prior reports must remain versioned; successful
replacement intentionally replaces the selected previous report.

All output symlinks, including dangling links and links to otherwise distinct
reports, are refused. Replacing a distinct hard-linked report replaces only the
selected directory entry, leaving its other names on their previous bytes.
Existing permission mode bits are copied, not ownership, access-control lists or
extended attributes. New reports use the temporary file's owner-only mode on
the tested POSIX platform. Use a caller-controlled ordinary directory and do not
concurrently change path bindings while saving. The second alias check reduces
an observed transition risk but is not a hostile filesystem-race guarantee.

The exercised pre-commit failures remove staging files and preserve prior bytes;
an operating-system refusal to remove a staging file is not guaranteed away.
Keyboard interruption propagates after cleanup rather than being reclassified
as CLI exit 2. Windows/filesystem variants, full-component discovery, repository-
wide suites and hosted main-binding gates were not executed by this contribution.
No live data, pricing, personal-history work, contact, scheduling or paid runner
is part of this delivery.
