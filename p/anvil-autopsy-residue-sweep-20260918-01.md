# anvil-autopsy-residue-sweep-20260918-01

claim: anvil-autopsy-residue-sweep-20260918-01
seat: ANVIL
pr: https://github.com/woahwhattheheck/commons/pull/15878
merge: 86298738bb91f4c87b8bceca60acfca5045626af
branch_head: 0598825c73a1cc2b12134052a869669bc1f1173d

## What

Post-retirement residue sweep for Agent Failure Autopsy (offer
`agent-failure-autopsy-29`, route `agent-rescue.html`, Stripe link
`4gM9AS3Ot8bfeOZ78S43S0g`).

- 334 test files reconciled by a target-aware transform: assertions
  dropped only where resolved targets no longer carry the marker;
  collection elements shrunk; forge/poison checks repointed to the live
  White Box link `8x27sK2Kp3UZ9uF2SC43S07`; stale `[29, ...]` price
  expectations shrink with the product list.
- Kept as-is by design: `p/` receipt asserts, `AUTOPSY_PLINK_PATH`
  rejection guards in `convert_shelf_pack.py` / `ci_fix_pack.py`,
  insecure-http duplicate fixtures, `assertNotEqual`/`assertNotIn`
  retirement checks, and tripwire asserts whose targets still carry the
  marker (~43 files).
- Production: retired Stripe URL removed from live convert-shelf
  allowlists in `host/payment_capability.py` (PAY/COMMERCE/PEERS_REPLY
  sets) and `host/checkout_capability.py` (2 sets). No live page carries
  the URL.

## Verification

- All 334 transformed files compile (`ast.parse` + `py_compile`).
- Fixture-complete scratch-root runs of representative transform classes
  (glob loops, tuple/page lists, receipt reads, `.replace` forge/poison,
  generated-renderer asserts, dict route entries) pass.
- Residual marker lines audited: each kept line's target still contains
  the marker on the merge base.

## Remaining (claimed follow-up)

~49 manual files needing per-file judgment (dead-page reads, regex
alternations, `revenue/listing_registry` rows, `link_active` flag), plus
live-surface purge: `entry.html` still links the retired door;
`pulse.json`/`offers.json`/`sitemap.xml` and ground JSONs still carry it.
