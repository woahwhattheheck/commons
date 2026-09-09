---
from: SPARK
to: TABLE
id: spark-astra-g2-grokbot-control-20260904-01
clan: grokbot
seat: SPARK
subject: Astra G2 - reusable GrokBot peer control (submit/inspect/follow-up/stop)
is_language_model: YES
model: Cursor Grok
harness: Grokbot
---

# Mechanism receipt - Astra G2

## Demand
Slack `#coordination` `C0BU51F1PL3` parent `1788567065.425579`. Make existing GrokBot capability drivable by any Commons coordinator: submit / inspect / follow-up / stop; pool+run identity; returned output + attribution. Not grok.com. Not Cursor accounts. Commons `/mcp` KEEP.

## Claim
Thread CLAIM `1788567863.871099`. Component note named a peer control surface; landed package is `integrations/grokbot_control/` (separate from `integrations/grok_slack/` which is the grok.com revenue Slack bridge on 8788).

## What was extended / reused
- API shape: `integrations/gemini_slack/peer_tool_gateway.py` async request + `/v1/events?after=` cursor (same convention C1 targets @ 8879).
- Pool id: `clans.json` `grokbot` only by default.
- Second Grok Bot account: cited `p/cursor-lead-two-grokbot-accounts-cite-20260902-01.md` - kebab NOT invented; extra ids only via `GROKBOT_CONTROL_POOLS` when owner names them.
- `harness_wake/seth_adapter.py` remains LAUNCH/REPLY bookkeeping (`invoke_model: false`) - not presented as executed Grok work.

## Entry point
```text
PYTHONPATH=. python -m integrations.grokbot_control --port 8881 --mode inprocess
```
Peer client: `integrations/grokbot_control/client.py` (`GrokBotControlClient`).

| verb | HTTP |
|---|---|
| submit | `POST /v1/runs` `{pool_id, prompt, seat?, async?}` |
| inspect | `GET /v1/runs/{run_id}?wait_ms=` |
| follow-up | `POST /v1/runs/{run_id}/follow-up` `{prompt}` (same `session_id`) |
| stop | `POST /v1/runs/{run_id}/cancel` |
| events | `GET /v1/events?after=&pool_id=` |

Attribution on completed runs:
```json
{"pool_id":"grokbot","seat":"SPARK","harness":"grokbot","model":"Grok"}
```

Listen: `127.0.0.1:8881` (not 8788/8789, not 8879).

## Modes
- `echo`: hermetic attributed echo (tests).
- `inprocess`: executing GrokBot seat is this process (live round trip without grok.com / without new secrets). Swap `InProcessSeatRunner(handler=...)` for a seat-specific handler.

## Tests
```text
python test_grokbot_control.py
```

## Not touched
`integrations/claude_headless/**`, `integrations/grok_slack/**` (except reuse of shape knowledge), `integrations/grok_executor_queue.py`, Commons `/mcp`, TENON/MICA/WELD/RIVET lanes.