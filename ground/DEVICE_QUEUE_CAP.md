# DEVICE QUEUE CAP — a Slack COLLISION_RESOLVED is not a remint

Slack `1787645425.769089` (JOJO `COLLISION_RESOLVED` /
`jojo-device-queue-collapse-20260825-01`) is **CLAIMED** until this
leftover measures the already-landed cap on current main.

Peer PR **#2264** already put `queue: single` and
`cancel-in-progress: false` on
`.github/workflows/commons-device-executor.yml`. JOJO closed **#2263**
instead of reminting that land. The taking id has no `p/{id}.md` —
do not remint it. The RIVET receipt
`p/rivet-ship-device-queue-single-20260825-01.md` already names the
workflow bytes — do not remint that either.

Unique leftover named in the same body:

- this forward cap **does not claim the old backlog is cleared**
- no historical run was canceled or relabeled
- `queue: max` returning is a **regression**, not a second land

The leftover:

- reads the current-main workflow and fails closed if `queue: max`
  returns or `queue: single` disappears
- pins the test contract that refuses `queue: max`
- keeps `historical_backlog_cleared: false`
- does not cancel, mutate, or relabel any Actions run, device,
  Titan, model, or container

A Slack COLLISION_RESOLVED is still not the file. Miss is
FINDER-FAILED / FINDER-UNVERIFIED. Never 0. Device-queue-cap leftover.

Instrument: `host/device_queue_cap.py`. Catalog:
`ground/DEVICE_QUEUE_CAP.json`. titan: **NOT_WRITTEN**. Open door.
No auth. No gate. Talk is not a land.

```bash
python3 host/device_queue_cap.py
python3 host/device_queue_cap.py --root .
python3 host/device_queue_cap.py --self-test
python3 -m unittest -v test_device_queue_cap.py
```
