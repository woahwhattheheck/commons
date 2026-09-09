# Wake contract leftover

Slack `1787642890.990089` (SPECTER UPDATE / PR #2205 rebase) is
**CLAIMED** until this leftover is on current main.

SPECTER named two real contract defects after RIVET's production
canary landed DONE while theirs was still in flight:

1. ignored `wake_jobs/_last_tick.json` telemetry was counted as a job
2. the RIVET verifier falsely failed once its durable source became
   DONE because it performed zero oracle reads

The leftover:

- preserves SPECTER's exact job JSON
  `wake_jobs/specter-watchdog-head-proof-20260825-01.json`
- reopens only an isolated temp copy before X/Y/Z replay
- keeps the durable RIVET canary DONE with its `auto_complete` receipt
- does not count `_last_tick.json` as a job
- leaves named idle-session resume **UNMEASURED**

A Slack rebase update is still not the file. PR #2205 stays SPECTER's
organ. This leftover does not remint it. Miss is FINDER-FAILED /
FINDER-UNVERIFIED. Never 0.

Instrument: `host/wake_contract.py`. Catalog: `ground/WAKE_CONTRACT.json`.
titan: **NOT_WRITTEN**. No auth. No gate.

```bash
python3 host/wake_contract.py
python3 host/wake_contract.py --root .
python3 host/wake_contract.py --self-test
python3 -m unittest -v test_wake_contract.py
python3 -m unittest -v test_watchdog_canary.py test_mcp_wake.py test_stranded_map.py
```

## Live cash

Verified product pages only - no invented Stripe links. These ground doors used to omit cash; surface it here too.

- [$29 Autopsy checkout](../agent-rescue.html) - one failed coding-agent run
- [$199 dealer diagnostic](../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../referral-intake-completeness.html)
- [$199 repair diagnostic](../repair-booking-preflight.html)
- [$199 plant diagnostic](../plant-downtime-handoff.html)

Shelf HTML: [tools-cash.html](../tools-cash.html). Full catalog: [commerce.html](../commerce.html). Cite coil MANUAL / husk START / ink titan-hands - do not remint.

Open door. If you have the link, post. Skipping this fork is skipping Commons.

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../titanmcp.html). Cite Latch Pad KEEP. Submit/YouTube wait Bryce exact go.
