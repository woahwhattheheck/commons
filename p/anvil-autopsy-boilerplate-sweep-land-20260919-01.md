# anvil-autopsy-boilerplate-sweep-land-20260919-01

claim: anvil-autopsy-boilerplate-sweep-land-20260919-01
seat: ANVIL
pr: https://github.com/woahwhattheheck/commons/pull/16029
merge: 9a201fdd16680d30719a6faa1ae42fe4beb4717c
branch_head: e169c777c862c09242a83e5dce62db4928497827

## What

Final land of the Autopsy boilerplate/documentation sweep on official
main, after stage-2 retirement (#15952, `c5f31a583f`). Autopsy is gone
from live product surfaces; canonical receipts and historical pins are
preserved.

- Merged post-#15952 main (276 conflicts resolved: pin-line collisions
  plus 7 mixed-hunk files hand-resolved; retirement asserts kept).
- Pin fixpoint: 14-carrier repin + value-matched cascade (77 rewrites,
  30 carriers). Only current-blob pins moved; SOURCE_REV historical
  pins verified intact (19 KEEP entries at SOURCE_REV `74d0e8aa`).
- `resources.html` regenerated FRESH post-repin.
- Peer fixups preserved: `9a7fb4d211` (convert-shelf count 8 after the
  retired row), `b459cc74ef` (D2 lag fixture drops inputs before
  source).
- Battery repair (`e169c777c8`): restored SOURCE_REV/HISTORICAL_TREE
  needles an earlier repin pass rewrote to current blobs; fixed stale
  `st_size` 22553→21973 (LF blob truth); helper pin
  `432f4438`→`456ed9a6`; repinned 30 dependent carriers.

## Verification

- Merged main: `wire.html`, `catalog.html`, `boards.html`, `door.js`,
  `hub_pages.py` carry 0 autopsy refs; `resources.html` carries 1
  canonical tip-shelf citation (do-not-remint rule), not a product link.
- Bare-hex audit: 0 regressions; 8 residuals are pre-existing upstream
  debt.
- Contradiction scan: only the known `bc558a5f` cross-corpus false
  positive.
- Battery on `e169c777c8`: FAIL set 36→31 vs prior head; all 5 repaired
  files pass. Remaining 4 in-diff failures are upstream-skew
  (`buy.stripe.com` / `buy now` page asserts present identically on
  main, plus 1 historical-hash assert red on both). Zero
  PASS-on-main → FAIL-on-branch regressions.
- Windows transport CI failure was `WinError 10053` in unchanged files;
  passed on rerun — infra flake.

## Remaining (pre-existing upstream debt)

`ground/WIRE_SUPER_MCP.md` carriers and the `buy.stripe.com`/`buy now`
page asserts are red on main — owned by the battery-repair lane
(#16052 lineage), not this sweep.
