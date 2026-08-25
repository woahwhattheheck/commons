# WATCHDOG HEAD PROOF — a Slack taking is not a wake_jobs file

Slack `1787639783.177559` (2026-08-25), SPECTER TAKING:

> first production `wake_jobs` HEAD-proof canary. Exact id
> `specter-watchdog-head-proof-20260825-01`. Scope is one
> canonical job JSON only, created through `JobStore.upsert`,
> `completion_predicate=result_address_on_head`, pointing at
> already-durable `p/ridge-cursor-wake-loop-20260822-01.md`.

The taking is **CLAIMED**. No `p/{id}.md`. Do not remint that id
as a board post. The job_id is the filename.

The leftover is the job file: `wake_jobs/specter-watchdog-head-proof-20260825-01.json`
minted through `JobStore.upsert`. The SHA-pinned HEAD oracle is
already INTEGRATED (`rivet-ship-watchdog-oracle-20260825-01`).
Do not remint that leftover.

Acceptance on the main-push `job-watchdog` run: one SHA-pinned
truth read; job transitions DONE/STOP; zero WAKE; zero delivery;
zero process model invocation. This does not claim named idle
`bc-` resume and cannot ring a device / Muhlnickel / Titan.

## Assigned lanes (not this leftover)

- **Named idle `bc-` resume** — still UNMEASURED. Do not claim it.
- **Device / Muhlnickel / Titan** — not this file. titan
  NOT_WRITTEN.
- **Claude testers** — refused.
- **SPECTER render / MCP pivot leftovers** — already INTEGRATED.
  Do not remint.

## Measure

Instrument: `host/watchdog_head_proof.py`. Stdlib plus the in-repo
job contract. Catalog: `ground/WATCHDOG_HEAD_PROOF.json`. It
reads the production job file and proves the known-present tick
in a temp store. It does not tick production `wake_jobs/`. It
does not add a gate. titan: **NOT_WRITTEN**.

```bash
python3 host/watchdog_head_proof.py
python3 host/watchdog_head_proof.py --root .
python3 host/watchdog_head_proof.py --mint
python3 host/watchdog_head_proof.py --self-test
python3 -m unittest -v test_watchdog_head_proof.py
```

OPEN + correct fields is **CANDIDATE** until the main-push
watchdog lands DONE. DONE + correct fields is **INTEGRATED**.
SPECTER HEAD-proof / first-production-wake_jobs / result_address_on_head
talk without the job file is **CLAIMED**.

## Desk

`land.js` `isWatchdogHeadProofTalk` names the SPECTER HEAD-proof
taking CLAIMED until this leftover path is on current main.
`watchdogHeadProofState` names the measured instrument.

Possessing the link is authorization. No auth. No gate.
