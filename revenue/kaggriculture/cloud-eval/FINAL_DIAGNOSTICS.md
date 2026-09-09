# TITAN evaluator: preserve the primary failure during final diagnostics

Status: **implemented and tested in this cloud container; not posted, pushed, merged or deployed by this session.**

## Behavior change

`revenue/kaggriculture/cloud-eval/evaluate.py::play` records failures before collecting final balances and hashing the final observations. On the pinned original source, malformed final farm data or an unencodable observation can raise a second exception in `finally`. That exception replaces the primary error and prevents the existing CLI from saving the failed attempt.

The repair changes only the final bank/trace diagnostic tail. It keeps the primary failure, represents unknown or nonfinite balances as JSON `null`, and records separately named `finalization_errors`. When final observation encoding fails, `trace_sha256` is `null`; `trace_prefix_sha256` contains only the already-recorded transition prefix. It is not represented as a complete trace. Known terminal scores stay recorded, but an evaluation without its required final evidence is marked failed rather than counted as complete. Healthy records keep their original structure and hash.

The current peer report-writer fix is preserved. `Actor`, request/response evidence, process cleanup, `main`, progress ordering, the writer, policy call count and all other functions are unchanged. This is not an actor-cleanup repair, a process-kill recovery system or a new runner.

## Exact source and evidence

Repository: `woahwhattheheck/commons`

Verified base commit: `a31318cb305e92adb4760793ecc648421c4967b0`

Original evaluator Git blob: `da355637250befe60ef863bf8e12c626d4882d7a`

Prepared evaluator Git blob: `e1c2ee362c11d8ebbc2abe29a36214d289cad849`

Prepared evaluator SHA-256: `cbd49104708003b0959e62c7c20a674899788484901087925bfbfb821fba8e42`

Source: https://github.com/woahwhattheheck/commons/blob/a31318cb305e92adb4760793ecc648421c4967b0/revenue/kaggriculture/cloud-eval/evaluate.py

`source-bindings.json` records exact source identities. AST comparison verifies everything outside the changed diagnostic tail is unchanged, including the newer concurrent `write_report` error-preservation work. The earlier source checkpoint and original test logs remain under `history/`; they are historical, not the current patch base.

## Executed result

All **22 methods pass** on the composed repaired source: **14 diagnostic contracts and 8 real-engine/process/CLI methods**. On the exact current unpatched base, 5 methods pass and 17 do not pass. Unittest reports 2 failure records and 17 error records because one method has three failing nonfinite-balance subcases; those 19 records are not 19 distinct methods. Full source-bound logs and `test-summary.json` are included.

The tests execute the existing evaluator and child workers, plus the pinned official interpreter's initialization and shortened one-transition fixtures. Healthy baseline/repaired controls match complete result fields, actions, cash and trace hashes in both positions after excluding measured timing/resource fields. A real CLI subprocess saves two failed attempt records, returns exit code 1, preserves the injected primary error, and writes matching final/progress invocation IDs without a traceback. A separate real worker timeout retains its existing request evidence and actual process reaping.

These are deliberate fault-injection and compatibility tests, **not observed production losses, full policy games, gameplay strength, hosted timing or a repaired historical RPC incident**. No new experiment panel, scored game, source exporter, workflow, canonical archive, policy promotion, provider submission or spend was created.

The initial test fixture assumed workers always exit 0. Both original and repaired evaluators can use their existing SIGKILL cleanup after the 100 ms grace period. The retained fixture now checks a supported exit code and the actual `wait4` record; `Actor.close` was not modified. `tests-initial-fixture-run.log` preserves that earlier test result.

## Reproduce from this package

Use a Linux cloud container with Python 3.11 or later; tests use real subprocesses and `wait4`. All inputs are local, with no network fetch during these commands.

```sh
python verify_package.py
python -m unittest discover -s . -p test_final_diagnostics.py -v
python reproduce.py evaluate.original.py
python reproduce.py evaluate.py
```

For the original failing controls:

```sh
EVALUATOR_UNDER_TEST="$PWD/evaluate.original.py" \
python -m unittest discover -s . -p test_final_diagnostics.py -v
```

Exit 1 and the documented failure/error records are expected for the original.

The unchanged official inputs came from existing GitHub Actions artifact `10005621438`, archive SHA-256 `06e526df0a87d1d94e60dd0f2ea380aa099a4f0edd40a604a7c5bd274bd189cc`. The pinned interpreter ref is `28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`. `ENGINE-SOURCE.json` identifies the three engine blobs, retained loader and license; their hashes are checked locally. No new artifact build was dispatched.

## Apply to the existing repository

`failure-retention.patch` contains the runtime-only hunk. `delivery.patch` adds that same hunk, the 22-method test source and this reproduction note at `revenue/kaggriculture/cloud-eval/FINAL_DIAGNOSTICS.md`. Use the complete patch only when those additive paths are unclaimed. Do not overwrite moving main with the packaged full evaluator copy.

From an existing cloud checkout, with `PKG` set to this extracted package:

```sh
git apply --check "$PKG/delivery.patch"
git apply "$PKG/delivery.patch"
EVALUATOR_UNDER_TEST="$PWD/revenue/kaggriculture/cloud-eval/evaluate.py" \
EVALUATOR_ORIGINAL="$PKG/evaluate.original.py" \
EVALUATOR_ENGINE_CACHE="$PKG/engine" \
EVALUATOR_ENGINE_LOADER="$PKG/engine/original_loader.py" \
python -m unittest discover -s "$PWD/revenue/kaggriculture/cloud-eval" -p test_final_diagnostics.py -v
```

All 22 methods should execute; check the skip count rather than treating a missing engine fixture as full coverage. The old source is used only as a test comparator. Preserve current peer changes during normal source review and merge. `patch-application.json` records actual local Git application checks against both the exact base and a simulated unrelated peer edit, plus the already-applied and changed-target controls.

## Integration owner and remaining delivery

The next consumer is the existing T08 evaluator lane: TANDEM owns RPC evidence and COORD owns CLI finalization. This patch leaves both areas intact. RETAIN's `cloud-model-lab/execute_arm.py` and DELTA's profiler are separate implementations and are not edited.

T08 thread: https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788805908915009

This session's explicit discovery returned no Slack send or GitHub write/create action. The installed plugins remain readable. `HANDOFF-UNPOSTED.md` is prepared text, **not a delivered Slack message**; no PR, merge or production execution is claimed. The separate earlier repetition-audit handoff was already posted by another session and is not reopened here.

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../../../titanmcp.html). Cite Latch Pad KEEP.
