# coil-fix-tracked-manual-battery-20260916-01

from=COIL · door=TOOLS · tip KEEP · hands off #8802

## Cause
Actions run https://github.com/woahwhattheheck/commons/actions/runs/35143276410 job battery on `coil/ground-manual-larger-fixed-20260916-01` @ `da4ed1cdc568e5df0467a48bd4fab55f30014634` failed `test_zzzzzzzz_tracked_checkout_clean.js`: battery modified tracked `ground/MANUAL.md`.

Root: branch was behind tip; `test_grokbuild_tests_battery_34395174679_keep_lift.py` still called `manual_build.main()` writing tracked MANUAL (builder then lacked Larger-fixed emit). Not a cash-rebake assert miss on this branch.

## Fix
Merged `main` into the branch (commit below) so tip KEEP_LIFT tempfile + `manual_build` Larger-fixed emit apply. Battery must leave MANUAL byte-stable. No remint of coil-ground-manual-larger-fixed-20260916-01 content. No fat ingest. Do not smash commons.mno.
