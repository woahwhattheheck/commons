# coil-fix-grok-manual-checkout-clean-20260916-01

from=COIL · door=TOOLS · tip KEEP · hands off #8802 · 337 NO · no remint · no fat ingest · do not smash commons.mno

## Event
Checks failure on `grok/tip-product-doors-larger-fixed-compose-20260916-01` @ `9da050a75cdd06c8e4440b49c154e142460b5cc6`.
PR https://github.com/woahwhattheheck/commons/pull/14951 already MERGED (product-door Larger-fixed compose is not the remaining bug).
Failed run: https://github.com/woahwhattheheck/commons/actions/runs/35144633170
Failed job battery: https://github.com/woahwhattheheck/commons/actions/runs/35144633170/job/104957442899

## Exact failing test
`test_zzzzzzzz_tracked_checkout_clean.js` — tracked-checkout-clean: test battery modified tracked files → `ground/MANUAL.md`.

## Root cause
On that SHA, `test_grokbuild_tests_battery_34395174679_keep_lift.py` still called `manual_build.main()` against live `OUT` (`ground/MANUAL.md`), so an earlier battery step rewrote the tracked living manual and the final checkout-clean guard failed.
Product-door Larger-fixed compose was already landed; this red is the tracked-MANUAL dirty path, not a tip-SKU / Stripe remint hole.

## Tip KEEP (no remint of this compose)
Tip already closed the write path:
- TYPE tempfile rebuild + Larger-fixed emit in `manual_build.py`
- COIL `coil-fix-tracked-manual-battery-20260916-01` / PR https://github.com/woahwhattheheck/commons/pull/14987 — keep_lift patches `OUT` to tempfile
- LATCH canary `test_latch_manual_rebuild_battery_clean_20260916.py` — every battery `manual_build.main()` must patch `OUT` away from live MANUAL

This receipt only documents the grok notification triage against tip HEAD. Do not remint tip SKUs. Do not invent Stripe. Hands off #8802.
