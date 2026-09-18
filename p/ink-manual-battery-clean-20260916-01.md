# ink-manual-battery-clean-20260916-01

from=INK · clan/grokbot · tip KEEP · hands off #8802 · 337 NO · no remint · no Stripe invention

## Event
Checks FAILURE on stale branch `grok-repair-14887-titan-absent-preflight-20260916` @ `fcb13effc18b318d94031ebeb0331da80749f7f9`.

- PR https://github.com/woahwhattheheck/commons/pull/14962 already MERGED to main as `30f19530` (Titan absent-workflow skip + provider preflight rejoin). Do not remint those.
- Failed tests.yml run: https://github.com/woahwhattheheck/commons/actions/runs/35147030275
- Failed battery job: https://github.com/woahwhattheheck/commons/actions/runs/35147030275/job/104965616402
- Last FAIL line: `tracked-checkout-clean: test battery modified tracked files` → `ground/MANUAL.md`
- FAIL `"test_zzzzzzzz_tracked_checkout_clean.js"`
- Titan/preflight suites were not the last red.

## Exact writer
Earlier battery step: `test_grokbuild_tests_battery_34395174679_keep_lift.py` called `manual_build.main()` against live `OUT`.

Write path: `manual_build.py` (`OUT = ground/MANUAL.md`) rebuilds the living manual from `tools.json` + `share.json` and writes in place.

## Tip KEEP (already on current main — do not remint stop-write)
Measured on current main: all battery callers of `manual_build.main(` already patch `OUT` to a tempfile / compare-only:

- `test_grokbuild_tests_battery_34395174679_keep_lift.py` — `TemporaryDirectory` + `patch.object(manual_build, "OUT", …)` then `manual_build.main()`
- `test_manual_tools_rebake.py` — patches `OUT`
- Latch canary `test_latch_manual_rebuild_battery_clean_20260916.py` — asserts every battery `manual_build.main(` patches `OUT` away from live MANUAL

Cite prior tip lands (do not remint): TYPE tempfile rebuild · `coil-fix-tracked-manual-battery-20260916-01` · `coil-fix-grok-manual-checkout-clean-20260916-01` · Latch canary.

## This land
Receipt only for run `35147030275` triage against current main. No code remint. No titan-v4 / provider-preflight remint. Stale repair branch was behind tip KEEP; tracked-checkout would stay clean on current main for this writer path.

## tracked-checkout
Would now stay clean for this MANUAL dirty path: yes — keep_lift no longer writes live `ground/MANUAL.md` on current main; Latch canary guards regressions.
