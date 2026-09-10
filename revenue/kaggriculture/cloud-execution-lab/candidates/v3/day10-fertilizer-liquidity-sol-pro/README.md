# TITAN V3 day-10 fertilizer liquidity — SOL-PRO

Operation: `TITAN-V3-DAY10-FERTILIZER-LIQUIDITY-20260910-01`

Slack claim: `#titan-kaggriculture` timestamp `1789067990.075559`.

## Narrow target

The strongest replay bridge already isolates TITAN's opening liquidity failure in episode `107130860`: at the four-HIRE boundary the rival has `$42`, TITAN has `$6`, the identical request costs `$7`, and TITAN loses the fourth worker plus 23 represented hand rows. Capillary owns deferred opening seed purchases and P07 owns actor remapping after an underfilled HIRE, so this lane does neither.

A separate trace census shows that TITAN produces large fertilizer volume but converts very little of it to cash. This candidate tests one distinct question: **can a certificate-preserving sale of genuinely executable fertilizer surplus increase day-10 liquidity without changing inherited unit work or market order timing?**

## Candidate boundary

`fertilizer_liquidity.py` is a pure, fail-closed proposal. It:

- mirrors the official interpreter's `max(1, maxMarketOrdersPerTurn)` limit;
- reads only the executable current prefix for ownership and conflicts;
- never treats an inactive suffix sale as cash, stock movement, or incumbent ownership;
- never edits or reorders an inherited executable row;
- appends after every inherited executable row, or fills only the first blank in a trailing run of active-prefix blanks;
- refuses an executable FERTILIZER sale or purchase already owned by the incumbent;
- retains a hard 24-unit shed reserve;
- stress-prices every unit after 32 hypothetical rival units and requires at least `$55` per unit;
- caps one lot at 64 units and stops at a `$12,000` observed-cash target; and
- runs only on zero-indexed days 8–10.

`candidate_runtime.py` installs per runtime instance at the exact final market-mutating seam: after canonical early-capital and final-pressure composition, before quadrant/spatial/history receipt commits. It reconstructs the exact post-unit snapshot and reruns TITAN's existing operating-stock certificate. An invented sale survives only when that certificate either withholds the required productive stock or proves that the proposed sale already leaves all certified obligations. Ambiguous cases restore the incumbent action and the prior snapshot.

Deadline fallback is untouched. No producer is called twice. The public runtime class is never monkeypatched.

## Dependency-complete carrier

`materialize.py` verifies the exact 428,158-byte canonical archive:

`5f6a4153e502713b9467776eafe7464af650584149173ce7507a31a1b2af60f1`

It rejects traversal, links/devices, duplicate members, unbounded member counts/bytes, missing `main.py`/`SOURCE.json`, extraction mismatch, and overlay collision. It independently extracts byte-identical control and candidate roots. The candidate differs only by four additive files:

- `fertilizer_liquidity.py`
- `candidate_runtime.py`
- `candidate.py`
- `panel_entry.py` (development telemetry only)

`candidate.py` reuses canonical `main.py::agent`, `_new_instance`, deadlines, resets, fallback, and package data. It changes only the per-instance final boundary. `panel_entry.py` is never the release entrypoint; it records bounded activation/decline evidence for hosted panels.

## Evidence and gate

Local exact bytes:

```text
python -m py_compile *.py
python -m unittest -v \
  test_fertilizer_liquidity.py \
  test_candidate_runtime.py \
  test_materialize.py \
  test_compare_panel.py

Ran 45 tests — OK
```

The path-scoped workflow:

1. binds the six source Git blobs and canonical archive identity;
2. reruns all 45 contracts;
3. proves independent control/candidate materialization;
4. imports both exact entries in isolated mode;
5. prepares the pinned official interpreter through the repository evaluator;
6. runs matched control and candidate panels against frozen Arlene, both seats, on four fixed seeds;
7. requires complete reports, identical engine/evaluator/loader/opponent/grid identities, distinct control/candidate entries, and instrumented activation evidence; and
8. reports own-cash deltas with seat-level non-regression. Margin-only movement cannot advance.

An `ADVANCE` result is a nomination for a broader champion panel, not promotion or submission authorization. `REGRESSION`, `MIXED`, and `NO_ACTION_SIGNAL` remain retained evidence.

## Exact source pins

- `main.py`: `4a8cf7bcda1f0fea231a144692cb84a779a9e73e`
- `titan_runtime.py`: `b952c9c228ecbde592bf3d2df01638677abb0d24`
- `scheduler.py`: `a483b24dd72b580d7d8811636b54d2d44f391575`
- `operating_stock.py`: `781aa90da0d85d0ba23c665e29d6087d182c085e`
- `mechanics.py`: `044a4f9c0a4a44dde10ada57563238bcaf82075d`
- `TITAN-CONFIG.json`: `3a3bef83899d3010fad623b628d9e95d9978111b`

## Scope lock

This branch is additive and default-off. It does not edit the canonical runtime, scheduler, operating-stock logic, configuration, archive, pointer, evaluator, opponent, provider state, Kaggle state, submission, or leaderboard entry. No win or score claim exists until the exact hosted panel finishes and its artifact is read back.
