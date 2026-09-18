# Owner pin placement ruling — 2026-08-30T06:10:00Z

The Claude backlog item `owner-pin-keep-placement-ruling` is resolved: keep one newest owner row above the newest chronological post.

## Decision

- Eligible owner labels remain `BRYCE` and `ZERO`.
- Keep exactly one owner pin.
- Place that pin at row 0, above the ordinary newest-first feed.
- After the pin, chronological rows remain time-sorted.
- Do not restore the old twelve-owner pin wall and do not create a side-by-side layout.

This is the smallest choice because it preserves the owner's standing request in a stable mobile/linear order without burying current work. A side-by-side presentation would add a responsive-layout choice and change the meaning of row order without improving the underlying feed.

## Current-main evidence

Fresh base: `1823f7ddb0728984aa67aff71146c44a370131ca`.

- `owner_pin.py` blob `76e19209130de284bc8885784208edd9d75b010e` sets `KEEP = 1`, selects the newest eligible owner row, removes its prior position, and prepends it.
- `test_owner_pin.py` blob `252962ef2e2e26bb10d9f0dd38767cec1941431c` asserts one BRYCE row at the front, the newest chronological row immediately after it, and no second owner-pin wall.
- At measurement time, `recent.json` blob `98df98a95da3fcf2bf8e589445624d66b9658b0e` had the single BRYCE pin first and a newer CODEX_LOCAL chronological row second.

The requested behavior is already implemented and test-pinned, so changing code or generated feed bytes would manufacture work. This receipt closes the missing ruling only.

## Boundaries

No `owner_pin.py`, test, generated feed, HTML, identity, auth, account, token, credential, device, outreach, payment, revenue, or cash state changed. No existing pin was reminted, moved, or deleted by this lane.
