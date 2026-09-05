# Transferable roles (Astra R4)

Slice: `hinge-transferable-roles-20260904-01`
Align: `hinge-r4-g2-access-routes-20260904-02` (SPARK G2 #8761)
CLI seat: `hinge-r4-cli-seat-20260905-01`
Bind route: `hinge-r4-bind-g2-session-20260905-01` (#8799 → `2ebc660`)
Release: `hinge-r4-release-occupant-20260905-01`

A **role** carries purpose, knowledge pointers, live obligations, tools, and
access routes. The current session is an **occupant**. Transfer changes the
occupant; `role_id`, purpose, and open `next_action` values stay put. Secrets
are never stored in the role — only named routes into existing stores/gateways.

## Entry points

```bash
python3 integrations/transferable_roles/cli.py create \
  --file integrations/transferable_roles/fixtures/synthetic_crm_followup_role.json \
  --store /tmp/hinge-roles

python3 integrations/transferable_roles/cli.py equip role-synthetic-crm-followup-20260904 \
  --session session-A --harness cursor-hinge --seat HINGE \
  --store /tmp/hinge-roles

python3 integrations/transferable_roles/cli.py bind-route role-synthetic-crm-followup-20260904 \
  --route grokbot_control_g2 --session-id g2-sess-1 --last-run-id run-9 \
  --store /tmp/hinge-roles

python3 integrations/transferable_roles/cli.py transfer role-synthetic-crm-followup-20260904 \
  --from-session session-A --to-session session-B --to-harness claude-tenon \
  --seat TENON --store /tmp/hinge-roles

python3 integrations/transferable_roles/cli.py release role-synthetic-crm-followup-20260904 \
  --from-session session-B --store /tmp/hinge-roles

python3 integrations/transferable_roles/cli.py export role-synthetic-crm-followup-20260904 \
  --store /tmp/hinge-roles

python3 integrations/transferable_roles/test_roles.py
```

`--seat` names the occupant (not `role_id`). Optional metadata for G2
attribution on session recover — never a Commons gate, never an admission
check, never blocks equip/transfer/release.

`bind-route` stamps durable `session_id` / `last_run_id` / optional `pool_id`
onto a named `access_route`. It does **not** copy occupant seat onto the route.

`release` clears the occupant so a later session can `equip` again. Bound route
fields and open obligations stay. Use `transfer` when handing to a known
successor; use `release` when the session ends without one yet.

## Access route shapes

### G2 — `kind: grokbot_control` (SPARK #8761 / `5154aa8f`)

Listen: `http://127.0.0.1:8881` (not grok.com `:8788`, not C1 `:8879`).
Client: `integrations/grokbot_control/client.py` (`GrokBotControlClient`).

A role `access_routes` entry should carry / recover:

| field | meaning |
| --- | --- |
| `pool_id` | GrokBot account pool (`grokbot` from clans.json; second account only via `GROKBOT_CONTROL_POOLS` when owner names it) |
| `session_id` | durable conversation across follow-ups (successor recovers from this, not live chat); stamp via `bind-route` |
| `last_run_id` | optional last actuation; stamp via `bind-route` |
| HTTP map | submit `POST /v1/runs`, inspect `GET /v1/runs/{run_id}`, follow-up `POST /v1/runs/{run_id}/follow-up`, cancel `POST /v1/runs/{run_id}/cancel`, session `GET /v1/sessions/{session_id}`, events `GET /v1/events?after=` |

Occupant **seat** lives on `occupant`, not on the route stamp path.
Point the role at **pool + session**; never bind the role to one chat window.
This package does **not** edit `integrations/grokbot_control/`.

### C1 / peer gateway — `kind: loopback_http`

Routes may also reference `integrations/gemini_slack/peer_tool_gateway.py`
fields: `submit` / `status` / `events` / `recover`. This module does **not**
edit that gateway or `integrations/claude_headless/`.

Service tags come from `ground/SLACK_SERVICE_TAGS.json` (Notion/MagicPath peer
notes already recorded by GOAT).
