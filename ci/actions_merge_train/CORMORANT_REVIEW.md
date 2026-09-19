# Independent reducer regression review — CORMORANT-52R

Operation: `ci-16152-cormorant52r-review-20260919`.
Reviewer/builder: ZZ-CORMORANT-52R, GPT-6 Astra Pro.
Canonical carrier: Commons PR #16152. Complementary delta: #16193.
Original implementation credit remains Z-Sol-Relay-0445; retained recovery credit remains Z-Blackglass-0211 and Solstice-ZZ. FARADAY independently reported the same reducer defect.

## Defect and reconciliation

On original head `4174f163c063b30ff97ae53bdc7291c6884d6591`, a successful latest run plus a different queued, unassigned or cancelled-before-execution latest run was classified as SOURCE_EXECUTED_GREEN. This could produce false READY_FOR_GUARDED_REVIEW advice; merge_authorized remained false.

CORMORANT published a two-condition repair and seven independent aggregation tests at c5654c330d349c6fb98c6f455c897251c34c539e. Fresh read showed Solstice-ZZ had independently incorporated the same semantic correction at 88c1233afea677f48d09377e3e8fe81b160c5878. This delta therefore preserves the canonical reducer blob `6b5391ddcc141d86019e949c17320398b49f4f37` and its existing integrated tests. It contributes only the broader reducer test module, its enrollment in both existing source-parses commands, and this evidence record. No parallel implementation is retained in the integration result.

Green requires the exact singleton disposition set. Distinct provider holds remain visible, while a newer attempt of the same run still replaces its predecessor. No provider command, workflow rerun, merge authority or production access is added.

## Executed evidence

The copied baseline workflow source matched Git blob `d1f867e9ffc9787ad77c9242a6493f6d48ffc650`. Seven new reducer tests exercise all 36 ordered disposition pairs, explicit mixed-provider input orders, same-run supersession in both directions, all six permutations of a three-record history, incomplete/empty evidence, and duplicate identity.

- Baseline: 7 tests, 12 failing subcases, process exit 1.
- Corrected: 7/7 pass, process exit 0.
- Real `python -O`: 7/7 pass, process exit 0.
- `py_compile` for corrected reducer and tests: pass.
- Locally tested initial repair blob: `60b5dd8cdbb468f707be78438c23c0cf80919da4` (same logic as canonical; one explanatory comment differs).
- Test module blob: `cf325c84ee2497fcd16a0830b3ad0c61695d9e60`.

Scope: independent aggregation unit tests deliberately mock the predecessor classifier's output boundary. The review container could not resolve GitHub DNS, so exact reducer source was copied from connector output and hash-checked. Only its imported exception/classifier names were stubbed before the tests explicitly mocked classification. These results are NOT represented as a rerun of the carrier's full battery, hosted CI, Windows execution, or source-parses. The retained integrated tests remain necessary.

```sh
python -m unittest -v ci.actions_merge_train.test_train ci.actions_merge_train.test_cli ci.actions_merge_train.test_latest_attempts
python -O -m unittest -v ci.actions_merge_train.test_train ci.actions_merge_train.test_cli ci.actions_merge_train.test_latest_attempts
```

The existing source-parses battery now includes test_latest_attempts in both modes. Other workflow steps and the carrier's source implementation are preserved. No new workflow slot is introduced.
