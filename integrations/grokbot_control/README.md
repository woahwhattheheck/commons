# grokbot_control (Astra G2)

Loopback peer gateway for **existing GrokBot pools** (not grok.com, not Cursor cloud accounts).
Default listen: 127.0.0.1:8881. Do **not** relaunch residents on the owner PC until the RAM incident is cleared.

## Run (tests / explicit owner start only)

```text
PYTHONPATH=. python -m integrations.grokbot_control --port 8881 --mode echo
PYTHONPATH=. python -m integrations.grokbot_control --port 8881 --mode inprocess
```

CLI memory floor (default 1024 MiB free; library/tests may pass 0):

```text
PYTHONPATH=. python -m integrations.grokbot_control --port 8881 --mode echo --min-free-mb 1024
```

Env override: GROKBOT_CONTROL_MIN_FREE_MB. Under the floor, POST /v1/runs returns **503** error=memory_guard and **does not** create a run record.

## HTTP

| verb | path |
|---|---|
| health | GET /health (also /) — includes memory_guard |
| pools | GET /v1/pools |
| submit | POST /v1/runs {pool_id, prompt, seat?, async?} |
| inspect | GET /v1/runs/{run_id}?wait_ms= |
| follow-up | POST /v1/runs/{run_id}/follow-up {prompt, async?} |
| cancel | POST /v1/runs/{run_id}/cancel |
| session | GET /v1/sessions/{session_id} |
| events | GET /v1/events?after=&limit=&wait_ms=&pool_id= |

Attribution on completed runs:

```json
{"pool_id":"grokbot","seat":"SPARK","harness":"grokbot","model":"Grok"}
```

Default pool id: grokbot from clans.json. Extra pool ids only via GROKBOT_CONTROL_POOLS when the owner names them (second-account kebab is not invented).

## Shared equipment

integrations.shared_equipment.peers.GrokBotEquipment exposes:

grokbot_submit, grokbot_inspect, grokbot_follow_up, grokbot_cancel, grokbot_session, grokbot_events, grokbot_pools, grokbot_health

grokbot_health is GET /health so peers can read memory_guard before submit. Wired into the Gemini peer tool gateway catalog beside Slack/GitHub/Gemini lifecycle tools. CLI: python -m integrations.shared_equipment.services catalog|call|manifest.

Peer client: integrations/grokbot_control/client.py (GrokBotControlClient).

## Tests

```text
python test_grokbot_control.py
python test_grokbot_shared_equipment.py
```
