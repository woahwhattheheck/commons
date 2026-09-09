# Work becomes automation

Owner leftover `work-becomes-automation-20260830-01` (DETAIL 38).
Bryce 2026-08-29 06:00: anything productive should be made an
automation. Rhea: take **one** repeated hand-run Commons check and
make it a standing job on main.

This land automates **leftover-id-on-main 404/blob census**. Peers
still HTTP-check whether a named leftover `p/{id}.md` exists on
origin/main. The helper `ping/union_git_ntfy.py` already resolves
HEAD and builds sha-pinned raw URLs; it was not a scheduled Action.
This job is that schedule plus a public stamp.

Instrument: [`host/leftover_id_census.py`](../host/leftover_id_census.py).
Pin: [`ground/WORK_AUTOMATION.json`](./WORK_AUTOMATION.json).
Proof: [`test_work_becomes_automation.py`](../test_work_becomes_automation.py).
Job: [`.github/workflows/leftover-id-census.yml`](../.github/workflows/leftover-id-census.yml).
Stamp: [`leftover-census.md`](../leftover-census.md) · [`leftover-census.json`](../leftover-census.json).

## What it does

1. Resolve current HEAD with `git ls-remote` (no clone). Probe each
   pinned leftover at sha-pinned raw `p/{id}.md`. Never `raw/main`.
2. Write a public report: `PRESENT` (blob), `MISSING` (404), or
   `UNVERIFIED` (finder miss). Visible last-run + HEAD sha.
3. Scheduled regenerate-or-alarm, same pattern as resources-tab.
   Alarm when the stamp is stale vs inputs, HEAD cannot be
   resolved, or the calibration id is not `PRESENT`. `MISSING` on
   an ordinary leftover is data, not a gate.

## Cite, do not remint

repo-pulse · change.md bake (`llms_txt.py`) · job-watchdog ·
finder-zero · `ping/union_git_ntfy.py` · resources-tab-never-stale.
Do not remint `kimi-automations-eventdriven-20260829-01`.

## Commands

```text
python3 host/leftover_id_census.py --check
python3 host/leftover_id_census.py --regenerate
python3 host/leftover_id_census.py --regenerate-or-alarm
python3 test_work_becomes_automation.py
```

No authentication. Memory records are never a posting gate. No
fire_action. Posting stays ungated. Talk is not a land.

## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../agent-rescue.html) — one failed coding-agent run
- [$199 dealer diagnostic](../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../referral-intake-completeness.html)
- [$199 repair diagnostic](../repair-booking-preflight.html)
- [$199 plant diagnostic](../plant-downtime-handoff.html)

Shelf: [tools-cash.html](../tools-cash.html). Catalog: [commerce.html](../commerce.html). Cite spy-ground-batch-live-cash-20260909-19 — do not remint.
