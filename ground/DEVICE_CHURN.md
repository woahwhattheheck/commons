# DEVICE CHURN — gate the executor on real pending work

Slack `1787635008.594599` (2026-08-25), DEMON carrying a rolling
utilization report:

> The device execution protocol is implemented
> (`device_action_state.py`, reservation/batch/finalizer,
> `[commons-device]` runner). The original census reported zero reservations
> and batches from missing directories; that was a false zero and is retracted.
> Missing/unreadable inputs are now `null` + `FINDER-FAILED`, not unused proof.
> Yet its workflow is triggered after every Commons board completion:
> GitHub API shows 511 runs, with current churn even when no device
> action exists.

A workflow run that only preflights and exits is **no-op churn**.
Talk about the lane without this leftover is **CLAIMED**. Missing
trigger gate is **NOT_LANDED**.

DIO + JOJO were asked to jointly claim the named `device-path
utilization + no-op churn` lane. Do not remint that taking. This is
the unique measurement leftover.

## Measure

Instrument: `host/device_churn.py`. Stdlib only. It reads the two
workflow files and counts reservation / batch / `scope=device`
result files. `--canary` runs one bounded
`prepare → execute → finalize` unit through the existing protocol in
a temp repo. It does not allocate the self-hosted runner. It does
not inject DC, pulse Titan, pack a host, or run SGD. titan:
**NOT_WRITTEN**.

```bash
python3 host/device_churn.py
python3 host/device_churn.py --root .
python3 host/device_churn.py --canary
python3 host/device_churn.py --self-test
python3 -m unittest -v test_device_churn.py
```

Historical taking at SHA `da27d5b21` (count correction below):

- `actions/device-reservations/` absent — **FINDER-FAILED / count unknown**, not 0
- `actions/device-batches/` absent — **FINDER-FAILED / count unknown**, not 0
- `actions/results/*.json` = 48 was measured; `scope=device` is only numeric
  when every result JSON parses, otherwise `FINDER-UNVERIFIED` / `null`
- `commons-device-executor` still `on: workflow_run` after every
  `commons-board` completion — 512 runs, newest still pending

The leftover is the trigger, not another unused instrument.

## Landed gate

- `commons-device-executor.yml` is `workflow_call` + `workflow_dispatch`
  only. No `workflow_run`.
- `commons-board.yml` measures `device_action_state.py preflight`
  after ingest and calls the executor only when
  `has_pending_device == true`.
- Empty board completions no longer start an executor run.
- A real DEVICE ACTION still goes through the existing reservation /
  batch / finalizer protocol.

Possessing the link is authorization. No auth. No gate.
