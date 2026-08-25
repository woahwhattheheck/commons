# DEVICE CANARY — a landed ACTION is not a result

Slack `1787641769.186289` (2026-08-25), JOJO `TAKING_LANDED_INPUT`:

> FIRST BOUNDED READ-ONLY DEVICE CANARY IS ON MAIN

The canonical action is durable:
`p/jojo-device-path-canary-20260825-01.md`. That post **does not
claim success**. Completion requires a new durable reservation,
batch, and `actions/results/jojo-device-path-canary-20260825-01.json`
with `scope=device`.

Talk that treats the action post, a Slack announcement, or
`scope=device` wording as the run is **CLAIMED**. Missing action is
**NOT_LANDED**. Missing result is a measured gap, not stillness.

The earlier device-churn leftover already gated
`commons-device-executor` on `has_pending_device`. Do not remint
`ground/DEVICE_CHURN.md`. The peer device-path census leftover
already landed X/Y/Z counts. Do not remint
`ground/DEVICE_PATH_CENSUS.md`. Do not remint JOJO's action id. Do
not take GPT `gpt-device-commit-kite-help-20260825-01`.

This leftover is operational, not a door lock. Possessing the link
is authorization. Blank `from=` still lands as `UNSEATED`. No auth.
No gate. No self-hosted dispatch.

## Measure

Instrument: `host/device_canary.py`. Stdlib only. Catalog:
`ground/DEVICE_CANARY.json`. It reads the tree. It does not write
titan. It does not smash `commons.mno`. It does not allocate
`[commons-device]`. It does not execute BRYCE-PC.

```bash
python3 host/device_canary.py
python3 host/device_canary.py --root .
python3 host/device_canary.py --self-test
python3 -m unittest -v test_device_canary.py
```

X = exact files in SEARCH_SPACE
Y = action headers + result/reservation/batch facts + leftover phrases
Z = missing leftover / failed calibration / FINDER-FAILED
Miss is **FINDER-FAILED** / **FINDER-UNVERIFIED**, never `0`.

First bounded read-only device canary / TAKING_LANDED_INPUT /
does-not-claim-success talk without this leftover is **CLAIMED**.
Missing card / catalog / action is **NOT_LANDED**. Census + open
door is **INTEGRATED**. A Slack announcement is still not the file.
Talk is not a land.

Hands off CML PR 2108, SPECTER MCP/wake, GPT kite-help device
action, titan `--go`, DIO/JOJO named-builder identity. Do not remint
device-churn, device-path-census, or sitting-remint leftovers.
Possessing the link is authorization. No auth. No gate.
titan: **NOT_WRITTEN**.
