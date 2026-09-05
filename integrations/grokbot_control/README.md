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
| submit | POST /v1/runs {pool_id, prompt, seat?, async?, case?} |
| inspect | GET /v1/runs/{run_id}?wait_ms= |
| follow-up | POST /v1/runs/{run_id}/follow-up {prompt, async?} |
| cancel | POST /v1/runs/{run_id}/cancel |
| session | GET /v1/sessions/{session_id} |
| events | GET /v1/events?after=&limit=&wait_ms=&pool_id= |

Optional `case` on submit (durable on the run from queued onward; follow-up inherits):

```json
{"offer_id":"sku-…","case_ref":"…","client_reference_id":"…","sku":"…"}
```

Only those four string keys are kept (max 200 chars each). Unknown keys dropped. Empty object omitted.

Autopsy fulfillers: build `case` with `case_from_autopsy_offer(case_ref=…, client_reference_id=…)` in `paid_case.py` (reads checked-in `revenue/agent_failure_autopsy/offer.json`). Pass the result to `GrokBotControlClient.submit(..., case=...)` or `grokbot_submit`. Does not remint Stripe.

Opaque paid-case receipt: `receipt_row_from_case(case, g2_run_id=…, g2_session_id=…)` builds a public seats `case_row` (no buyer PII). Shape lives on `revenue/agent_failure_autopsy/seats.json` `case_row_shape`; `case_rows` stay empty until `REAL_STRIPE_PAYMENT_OBSERVED`. Hermetic pin: `python test_grokbot_paid_case_receipt.py`.

X-campaign door: `agent-rescue.html` stamps `client_reference_id=afa29_x_a_v1` for exact `utm_source=x` / `utm_medium=paid_social` / `utm_campaign=agent_failure_autopsy_29`. Hermetic pin: `python test_grokbot_client_reference_roundtrip.py`.

Attribution on completed runs:

```json
{"pool_id":"grokbot","seat":"SPARK","harness":"grokbot","model":"Grok"}
```

Default pool id: grokbot from clans.json. Extra pool ids only via GROKBOT_CONTROL_POOLS when the owner names them (second-account kebab is not invented).

## Shared equipment

integrations.shared_equipment.peers.GrokBotEquipment exposes:

grokbot_submit, grokbot_inspect, grokbot_follow_up, grokbot_cancel, grokbot_session, grokbot_events, grokbot_pools, grokbot_health

grokbot_submit accepts optional `case`. grokbot_health is GET /health so peers can read memory_guard before submit. Wired into the Gemini peer tool gateway catalog beside Slack/GitHub/Gemini lifecycle tools. CLI: python -m integrations.shared_equipment.services catalog|call|manifest.

Peer client: integrations/grokbot_control/client.py (GrokBotControlClient).

## Tests

```text
python test_grokbot_control.py
python test_grokbot_shared_equipment.py
python test_grokbot_paid_case.py
python test_grokbot_paid_case_receipt.py
python test_grokbot_client_reference_roundtrip.py
```
