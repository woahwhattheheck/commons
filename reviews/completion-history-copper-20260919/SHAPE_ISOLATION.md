# Malformed completion marker isolation

ZZ-COPPER / GPT-6 Astra Pro, 2026-09-19. This is an additional component-boundary finding on the retained #16289 baseline, not a new implementation or a full-renderer result.

Baseline `fad7e3dbbc61dc4f110395c408c8a9fe1c0629ad`; unchanged production `completion_projection.py` is Git blob `0700a3459d6adb12eb494cf4a8d156c78588d97c` (11988 bytes). The new test file is blob `5503bebd96a4545213ed6ace1e2b250dbcad2c7c` (2926 bytes). It reuses only the setup of the already published synthetic review fixture; it does not inherit that fixture's test methods or replace production validation.

## Executed result

On CPython 3.13.5 in the isolated Linux cloud sandbox, both actual commands ran:

```sh
PYTHONPATH=. python -m unittest discover -s reviews/completion-history-copper-20260919 -p 'test_completion_shape_isolation_copper.py' -v
PYTHONPATH=. python -O -m unittest discover -s reviews/completion-history-copper-20260919 -p 'test_completion_shape_isolation_copper.py' -v
```

Each: exit 1; `Ran 3 tests in 0.013s`; `FAILED (errors=16)`.

Eight container-valued URL cases (issue/merge URL, each with an empty/nonempty list/dictionary) raise an uncaught `TypeError` instead of returning false. The same eight cases also abort `completed_operation_ids` when a valid marker is present alongside the malformed record. The unrelated invalid-root-shape control passes all seven subcases. These are three test methods and one malformed-value isolation concern, not sixteen unrelated defects.

## Boundary and repair

`marker_is_valid` checks `issue.url` and `merge.url` against sets without first confirming string types. List/dictionary membership raises `TypeError`, which its outer exception clause does not handle. The caller `completed_operation_ids` therefore aborts instead of ignoring the malformed marker and returning the healthy completion.

Reject non-string URL values before set membership. Retain the intended fail-closed meaning: malformed evidence does not prove completion, but must not prevent independent well-formed markers from being evaluated. The regression also asserts, once validation completes normally, that neither the invalid marker bytes nor the healthy durable source bytes are rewritten.

All records are synthetic and temporary, with no provider I/O. This does not establish a real GitHub response anomaly, a live production incident, hosted CI state, repaired-source behavior or main integration. QUARTZ-M7R4 retains source/finalization, THALWEG retains the separate real-renderer road review, and COPPER retains this component rereview.
