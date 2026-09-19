# Completion timestamp matrix: baseline execution

ZZ-COPPER / GPT-6 Astra Pro, 2026-09-19. This extends the component evidence in `EXECUTION.md`; it is not a second implementation or full-renderer claim.

Baseline: `fad7e3dbbc61dc4f110395c408c8a9fe1c0629ad`.
Production module Git blob: `0700a3459d6adb12eb494cf4a8d156c78588d97c` (11988 bytes, unchanged).
New test Git blob: `708ca11a910c89ad5585babe73992c65dddfc4e9` (4959 bytes).
Environment: CPython 3.13.5, isolated Linux cloud sandbox.

## Property checked

A completion decision must compare the represented instants, not the lexical order of their UTC-offset representations. The independent oracle constructs three known UTC instants around midnight and represents each under four offsets: -07:00, +00:00, +02:00 and +05:30. All nine merge/close instant pairs are checked under all sixteen representation pairs, including equality and date rollover.

This yields 144 chronological cases at `build_marker` and the same 144 at `marker_is_valid`. There are also four timezone-naive inputs at each boundary, plus a positive canonical-UTC case that checks original timestamp strings remain unchanged. The test creates actual temporary source files and imports the unchanged production module. Provider responses and the ancestry callback are synthetic; no URL is fetched.

## Commands actually executed

```sh
PYTHONPATH=. python -m unittest discover -s reviews/completion-history-copper-20260919 -p 'test_completion_time_matrix_copper.py' -v
PYTHONPATH=. python -O -m unittest discover -s reviews/completion-history-copper-20260919 -p 'test_completion_time_matrix_copper.py' -v
```

Normal output: exit 1; `Ran 5 tests in 0.028s`; `FAILED (failures=116)`.
Optimized output: exit 1; `Ran 5 tests in 0.062s`; `FAILED (failures=116)`.

The same subcases fail in both modes:

| Boundary | Executed subcases | Failed subcases |
| --- | ---: | ---: |
| Builder chronology matrix | 144 | 54 |
| Reader chronology matrix | 144 | 54 |
| Builder timezone-naive rejection | 4 | 4 |
| Reader timezone-naive rejection | 4 | 4 |

The canonical-UTC preservation control passes. This is **five test methods with 296 matrix/naive subcases**, not 296 distinct test methods. The 116 failed subcases exercise the timestamp-validation/order concern already reported on #16289, not 116 unrelated defects.

The matrix supplies both valid and invalid ordering examples for the source owner's parsed-chronology repair. It does not establish a real GitHub payload anomaly, a production incident, new source correctness, hosted CI status or main integration. QUARTZ-M7R4 retains source and finalization custody.
