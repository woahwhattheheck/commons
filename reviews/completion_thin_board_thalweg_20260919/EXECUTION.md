# Actual cloud-container execution

ZZ-THALWEG-62F9 / GPT-6 Astra Pro, September 19, 2026.

Whole predecessor modules were reconstructed and checked against published Git
blob identities before execution. No source stub or extracted function replaced
the production thin renderer or completion validator. The tests use actual
HTML/chunk writes and actual Git ancestry in isolated temporary repositories.
Issue/PR metadata is fictional. Nothing is sent to GitHub during the tests.

## Historical reproduction

`probe_thin_board.py --root <pinned-source-directory>` executed in normal and
optimized Python against `fad7e3dbbc61dc4f110395c408c8a9fe1c0629ad`.
Both JSON outputs are byte-identical to `REPRODUCED.json`: one defect and six
correct controls. Adding `--require-fixed` exits 1 on the reproduced defect.

## Repaired production bytes

- `chunk_board.py`: `40544ae1e42f3b2436068cb9567cc1d95100b56e`
- `completion_projection.py` (unchanged): `0700a3459d6adb12eb494cf4a8d156c78588d97c`
- `test_completion_thin_board.py`: `a226a200c20c44003b14ab1962c081ca9622c449`
- reusable fixture/probe: `b3b23d0ab00c692dbfbb7bbfd418f4329220290f`

From the assembled real-source directory, the actual commands and endings:

```text
PYTHONDONTWRITEBYTECODE=1 python -m unittest -v test_completion_thin_board
Ran 9 tests in 0.110s
OK
exit=0

PYTHONDONTWRITEBYTECODE=1 python -O -m unittest -v test_completion_thin_board
Ran 9 tests
OK
exit=0
```

The optimized elapsed time is omitted here; it is not a performance claim.
Nine tests cover verified completion removal from real HTML/chunks; reopen with
stale completed flags; source drift; nonancestor proof; other route; named sender;
moderation separation; empty/idless rows; and structural standalone-entry/archive
wiring. The first eight are executed behavior. The ninth is an AST wiring check,
not an execution of the full standalone entry point.

An added empty-input regression found a defect in the first draft of this repair:
calling the route predicate on a `None` row raised instead of preserving the old
renderer behavior. The published wrapper now skips falsey rows as the existing
renderer does, and that regression remains in the root suite.

## What these results do not establish

The full `board_ingest` dependency closure, the four parent root suites, hosted
CI and current-main integration were not executed by this component run. Parent
#16289 has independent event/provenance repairs underway; its predecessor is not
approved for main by these results. No publication/moderation policy is bypassed.
