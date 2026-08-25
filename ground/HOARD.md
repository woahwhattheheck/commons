# HOARD — session bytes are not current main

Owner Slack `1787627026.727319` (2026-08-25):

> YOU ALL NEED TO BE COMMITTING AND PUSHING ALL OF YOUR BUILDS DO
> NOT HOARD SHIT IN YOUR SESSION AND MAKE ME TRACK IT DOWN

Uncommitted or unpushed work is **NOT_LANDED**. A Slack yell is
**CLAIMED**. A branch or PR is still not official `main`.

## Measure this clone

Instrument: `host/session_export.py`. Stdlib only. It reads `git
status --porcelain` and `origin/main..HEAD`. It does not write. It
does not add a gate. titan: **NOT_WRITTEN**.

```bash
python3 host/session_export.py
git status --short
git log --oneline origin/main..HEAD
git push -u origin HEAD
```

Then finish the merge onto current main. Verify the exact path at
the official SHA. Talk is not a land.

## Desk

`land.js` `isHoardTalk` names the owner copy CLAIMED until a leftover
path is on current main. `sessionExportState` names dirty/unpushed
`NOT_LANDED`, a still-ahead push `CANDIDATE`, and a clean clone
`INTEGRATED` for that working tree only.

Do not remint `rivet-ship-browser-return-20260825-01`. Do not treat
this card as permission. Possessing the link is authorization.
