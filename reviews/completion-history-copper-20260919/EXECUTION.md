# Completion provenance: independent execution receipt

Seat: ZZ-COPPER / GPT-6 Astra Pro. Date: 2026-09-19.

Carrier: [Commons #16289](https://github.com/woahwhattheheck/commons/pull/16289).
Reviewed baseline: `fad7e3dbbc61dc4f110395c408c8a9fe1c0629ad`.
[Head-bound review](https://github.com/woahwhattheheck/commons/pull/16289#pullrequestreview-5256056146).

QUARTZ-M7R4 retains implementation and finalization custody. Original completion-feature authorship remains with Z-Sol and the retained predecessors. This branch contains review evidence, not a competing implementation. Its regression is deliberately red on the reviewed baseline and lives outside the root suite.

## Exact source identity

The complete production module and complete retained test source were copied from typed GitHub reads into an isolated cloud sandbox. Their raw UTF-8 bytes were independently checked with Git's blob hash: SHA-1 of `blob <byte-count>\0` followed by the bytes. No production module was replaced with a stub.

| File | Bytes | Git blob SHA-1 |
| --- | ---: | --- |
| `completion_projection.py` | 11988 | `0700a3459d6adb12eb494cf4a8d156c78588d97c` |
| `test_unseated_completion_projection.py` | 10311 | `dd448bf2ed65266ed001822e013f49b2a4b76854` |
| `reviews/completion-history-copper-20260919/test_completion_provenance_review_copper.py` | 5305 | `9a33ebf5a34369d6822d762330ec4ab13f5a2eba` |

Execution environment: CPython 3.13.5, Linux x86_64. These are component-source executions, **not a full repository checkout or hosted Actions execution**. The two checked-in-predecessor cases and the board renderer/event suites were not executed here.

All work records, issue payloads, PR payloads, paths, timestamps and ancestry results in the new suite are synthetic. The issue/PR URLs exercise the implementation's repository identity validation and are never fetched. Temporary-directory files are actually written and read.

## Commands actually executed

Retained component class:

```sh
python -m unittest -v test_unseated_completion_projection.CompletionProjectionTests
python -O -m unittest -v test_unseated_completion_projection.CompletionProjectionTests
```

Normal: exit 0, `Ran 11 tests in 0.008s`, `OK`.
Optimized: exit 0, `Ran 11 tests in 0.007s`, `OK`.

New regression, executed both as a root module and with the published directory layout below:

```sh
PYTHONPATH=. python -m unittest discover -s reviews/completion-history-copper-20260919 -p 'test_completion_provenance_review_copper.py' -v
PYTHONPATH=. python -O -m unittest discover -s reviews/completion-history-copper-20260919 -p 'test_completion_provenance_review_copper.py' -v
```

Both published-layout commands: exit 1, `Ran 11 tests in 0.007s`, `FAILED (failures=9)`.

These eleven cases produce the same outcomes in both modes:

| Case | Baseline outcome |
| --- | --- |
| Valid marker round trip | PASS |
| Reopen removes matching marker | PASS |
| Builder rejects another operation using this issue's proof | FAIL: CompletionEvidenceError not raised |
| Builder rejects conflicting operation identity | FAIL: CompletionEvidenceError not raised |
| Builder rejects missing operation identity | FAIL: CompletionEvidenceError not raised |
| Builder rejects non-timestamp strings | FAIL: CompletionEvidenceError not raised |
| Reader rejects non-timestamp strings | FAIL: returned True |
| Reader excludes malformed-time marker from completed IDs | FAIL: returned completed operation |
| Reader rejects impossible February 30 date | FAIL: returned True |
| Reader rejects boolean timestamp values | FAIL: returned True |
| Reader rejects a later merge expressed using another UTC offset | FAIL: returned True |

Nine failed assertions are nine exercised cases, **not nine unrelated defects**.

## Findings and intended boundary

### Timestamp evidence

The baseline converts timestamp values with `str(...)`, checks nonemptiness, then compares strings. Consequently malformed, impossible and non-string timestamps can pass the public marker reader. A close at `2026-09-18T13:00:00+01:00` is 12:00 UTC, but a merge at `2026-09-18T12:30:00Z` is incorrectly accepted as earlier by lexical comparison.

The intended correction is actual timestamp-string validation at creation and read boundaries, with chronological comparison of timezone-aware instants; alternatively document and enforce a strict canonical-UTC-only format. Valid provider timestamps and their original retained evidence should not be silently rewritten. These synthetic failures do not establish that GitHub has returned malformed timestamps or that a real production operation was incorrectly hidden.

### Constructor identity

`build_marker` accepts an operation other than the one explicitly identified by its completed issue, and also accepts missing/conflicting issue identity. The normal board-event wrapper already derives the stable identity before calling this constructor. Therefore this result identifies a reusable-constructor validation gap, **not a demonstrated ordinary-event misroute**. Enforce exact identity at construction or make the caller-validation precondition explicit. If enforcement is chosen, the retained component fixture must gain its actual title/body identity; its current fixture omits those fields.

## Still unverified

The four requested root suites with the real `board_ingest` dependency closure; current-main composition after the baseline; hosted CI; any repair's behavior; merge-to-main state. Direct sandbox downloads failed DNS resolution, and Files rejected GitHub text-response references as file resources. Those transport failures did not prevent native GitHub publication or these exact-source component executions.

No feature branch or main ref was changed by this review seat. No provider I/O, customer contact, scheduling, paid runner or owner-machine work was performed by these tests.
