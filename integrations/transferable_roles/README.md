# Transferable roles (Astra R4)

Slice: `hinge-transferable-roles-20260904-01`
Align: `hinge-r4-g2-access-routes-20260904-02` (SPARK G2 #8761)
CLI seat: `hinge-r4-cli-seat-20260905-01`
Bind route: `hinge-r4-bind-g2-session-20260905-01` (#8799 → `2ebc660`)
Unbind route: `hinge-r4-unbind-route-20260905-01`
Release: `hinge-r4-release-occupant-20260905-01`
Advance: `hinge-r4-obligation-advance-20260905-01` (#8812 → `8a344d54`)
Import: `hinge-r4-import-package-20260905-01`
Paid fulfillment: `hinge-r4-paid-fulfillment-role-20260905-01`
Checkout wire: `hinge-r4-autopsy-checkout-wire-20260905-01`
Spine pointers: `hinge-r4-autopsy-spine-pointers-20260905-01`

A **role** carries purpose, knowledge pointers, live obligations, tools, and
access routes. The current session is an **occupant**. Transfer changes the
occupant; `role_id`, purpose, and open `next_action` values stay put. Secrets
are never stored in the role — only named routes into existing stores/gateways.
**Roles confer no credential access** — owner policy keeps tokens in existing
secure stores; this package only names routes.

## Entry points

```bash
python3 integrations/transferable_roles/cli.py create \
  --file integrations/transferable_roles/fixtures/synthetic_crm_followup_role.json \
  --store /tmp/hinge-roles

python3 integrations/transferable_roles/cli.py create \
  --file integrations/transferable_roles/fixtures/synthetic_agent_failure_autopsy_role.json \
  --store /tmp/hinge-roles

python3 integrations/transferable_roles/cli.py equip role-synthetic-crm-followup-20260904 \
  --session session-A --harness cursor-hinge --seat HINGE \
  --store /tmp/hinge-roles

python3 integrations/transferable_roles/cli.py bind-route role-synthetic-crm-followup-20260904 \
  --route grokbot_control_g2 --session-id g2-sess-1 --last-run-id run-9 \
  --store /tmp/hinge-roles

python3 integrations/transferable_roles/cli.py unbind-route role-synthetic-crm-followup-20260904 \
  --route grokbot_control_g2 --store /tmp/hinge-roles

python3 integrations/transferable_roles/cli.py transfer role-synthetic-crm-followup-20260904 \
  --from-session session-A --to-session session-B --to-harness claude-tenon \
  --seat TENON --store /tmp/hinge-roles

python3 integrations/transferable_roles/cli.py release role-synthetic-crm-followup-20260904 \
  --from-session session-B --store /tmp/hinge-roles

python3 integrations/transferable_roles/cli.py advance-obligation role-synthetic-crm-followup-20260904 \
  --id ob-1 --status done --next-action "Recorded next CRM action from stored evidence" \
  --evidence-pointer p/hinge-r4-obligation-advance-20260905-01.md \
  --store /tmp/hinge-roles

python3 integrations/transferable_roles/cli.py open-obligations --store /tmp/hinge-roles

python3 integrations/transferable_roles/cli.py export role-synthetic-crm-followup-20260904 \
  --store /tmp/hinge-roles

python3 integrations/transferable_roles/cli.py import \
  --file /tmp/role-export.json --store /tmp/hinge-roles-successor

python3 integrations/transferable_roles/test_roles.py
```

`--seat` names the occupant (not `role_id`). Optional metadata for G2
attribution on session recover — never a Commons gate, never an admission
check, never blocks equip/transfer/release.

`bind-route` stamps durable `session_id` / `last_run_id` / optional `pool_id`
onto a named `access_route`. It does **not** copy occupant seat onto the route.

`unbind-route` clears stamped recover fields on a named `access_route`. Default
clears `session_id` and `last_run_id` only (keeps fixture `pool_id`). Pass
`--fields session_id,last_run_id,pool_id` to also clear `pool_id`. Route shell
(name/kind/urls) and purpose/obligations/occupant stay.

`release` clears the occupant so a later session can `equip` again. Bound route
fields and open obligations stay. Use `transfer` when handing to a known
successor; use `release` when the session ends without one yet.

`advance-obligation` stamps `status` / `next_action` / `evidence_pointer` on one
obligation. Purpose and sibling obligations stay. Allowed statuses:
`open|done|blocked|deferred`. Roles still confer no credentials.

`open-obligations` scans every role in the store and returns open rows as
`{"open_obligations": [...]}` with `role_id`, optional `label`, `purpose`,
`obligation_id`, `summary`, `next_action`, optional `evidence_pointer` /
`synthetic`, sorted by `(role_id, obligation_id)`.

`import` adopts an `export` package into an empty store with the same `role_id`
(no remint, no overwrite). Occupant is cleared so the importer must `equip`.
Bound route session fields survive.

## Paid fulfillment handoff

SYNTHETIC fixture
`fixtures/synthetic_agent_failure_autopsy_role.json` packages one paid
**Agent Failure Autopsy** ($29 one-time) fulfillment for seat-to-seat handoff:
open obligations `ob-intake` → `ob-diagnose` → `ob-review` → `ob-settle`
(deliver **or** refund). Reuses CRM-shaped `grokbot_control_g2` +
`gemini_peer_tool_gateway`, plus `payment_capability` (`kind: public_html`
pointing at `payment-capability.html` / `pay.html`). Knowledge cites
`ground/PAYMENT_CAPABILITY.md`, live checkout on `agent-rescue.html` (#8889),
and **pointer-only** into landed #8811 spine under `revenue/agent_failure_autopsy/`
(README / RUNBOOK / offer.json / report-template + `fulfillment.py` tool entry) —
**do not invent plink**, do not remint spine. No credential remint; roles confer
no Stripe access. Use `open-obligations` to see remaining open work across roles
after a transfer.

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
