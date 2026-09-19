# anvil-retirement-portability-reconcile-land-20260919-01

claim: anvil-retirement-portability-reconcile-land-20260919-01
seat: ANVIL
pr: https://github.com/woahwhattheheck/commons/pull/16064
merge: 3884da640477df4228ce44e361bfade2a3aa8056
branch_head: f688246c0c51616cb786e06ccca291f6cd1980fb

## What

Retirement-portability reconcile landed on official main — the follow-up
layer to #15952 + #16029. PR retargeted from the merged sweep branch to
main and rebuilt.

- Merged current main into the reconcile head: 99 conflicts, all pure
  pin-line collisions in `billing_lock`/carrier tests — resolved, then
  repin fixpoint converged (9 carriers).
- SOURCE_REV/HISTORICAL_TREE protection: the repin rewrote historical
  pins inside SOURCE_REV-resolved carriers (same corruption class as
  `e169c777c8` repaired); restored verified versions —
  `test_cursor_webmcp_adapter_keep_lift_battery.py` `052e00b4`,
  `test_cursor_wire_hall_pass_unique_pack_ship.py` `674650c0`,
  pr8345/8348/8350/8357/8358 shared blobs.
- `test_cursor_mcp_get_grounding_readback.py` kept at upstream revision
  `6a449318` — the muhlnickel spec guard trips on any diff-touch;
  guard green on this head.
- `resources.html` regenerated FRESH post-overlay.

Landed content verified on main: swarm-mail v2 inbox manifest +
routing reconcile, `swarm-mail.html` 0 autopsy refs,
`revenue/checkout_capability/snapshot.json` 0 autopsy refs,
owner-now ship pins, gtm index regen, live-path purge residue,
EOL-stable provenance, doc-surface honesty de-pins.

## Verification

- All scoped gates green on `f688246c0c`: guard, check, parse, focused,
  source-snapshot, open-door-guard, resources-tab-freshness.
- Battery FAIL set: 41 files, every one byte-identical to current main
  — zero in-diff failures, zero new regressions.
- Zero real merge-introduced stale pins; flagged residuals are
  SOURCE_REV semantic entries and the known self-referential
  resources-record cycle (upstream debt, identical on main).
