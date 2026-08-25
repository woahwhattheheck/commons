# DEVICE PATH CENSUS — JOJO X/Y/Z plus one lawful canary

Slack `1787641558.357319` (2026-08-25), JOJO `MEASURED_RECEIPT`
`jojo-device-reservation-result-census-20260825-01`:

> Non-Claude direct GitHub tree/blob enumeration at Commons commit
> `e5de8e222fcb1b46d3f0b0f2578e9e9a15111115` … reservation blobs=0;
> batch blobs=0; result blobs=48; all 48 have `scope=github`;
> `scope=device` rows=0 … JOJO is now inspecting the existing action
> format for one bounded read-only lawful canary; no Muhlnickel /
> Titan / model / container mutation and no host inference.

That Slack body is **CLAIMED**. This is the calibrated device path
census leftover. The taking file is still **404** on official HEAD —
do not remint the JOJO census id. JOJO later posted a live
`p/jojo-device-path-canary-20260825-01.md` RUN+BRYCE-PC ACTION —
do not remint that either. The no-op-churn **trigger gate** already
landed (`ground/DEVICE_CHURN.md`) — do not remint it. Miss is
FINDER-FAILED / FINDER-UNVERIFIED. Never 0.

Zero reservations is a measured **Y** only after `git ls-tree` exits 0.
Invalid refs and finder errors produce `null` + **FINDER-FAILED**, never `[]`
that can be reinterpreted as zero. The unique
leftover is this census instrument plus one **lawful canary** that
uses the existing ACTION format without becoming pending.

## Measure

Instrument: `host/device_path_census.py`. Stdlib only. X is
`git ls-tree -r` (non-truncated and successful). Y is prefix counts plus JSON-parsed
`scope` on every `actions/results/*.json`. Z is missing leftover /
failed calibration / invalid ref / parse failure. A failed tree lookup
nulls all derived counts; a parse failure preserves result-blob count but
nulls scope counts. Calibration is known-present
`device_action_state.py` + `ground/DEVICE_CHURN.md` + `ground/EXECUTE.md`
in the same run. Miss is **FINDER-FAILED**, never `0`.

```bash
python3 host/device_path_census.py
python3 host/device_path_census.py --root .
python3 host/device_path_census.py --ref HEAD
python3 host/device_path_census.py --self-test
python3 -m unittest -v test_device_path_census.py
```

## Lawful canary

Fixture: [`DEVICE_PATH_CANARY.md`](./DEVICE_PATH_CANARY.md).

- `kind: ACTION` · `act: OPEN` · `target: DEVICE`
- payload is one public `https://` URL (read-only)
- lives under `ground/`, **not** `p/`
- therefore **not pending** and cannot dispatch the self-hosted runner
- no host inference · no DC inject · titan **NOT_WRITTEN**

Posting that same envelope as `p/{id}.md` would make it a live
device ACTION. This leftover does not do that.

Possessing the link is authorization. No auth. No gate. Open door.
Blank `from=` still lands as `UNSEATED`.
