# Transferable roles (Astra R4)

Slice: `hinge-transferable-roles-20260904-01`

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
  --session session-A --harness cursor-hinge --store /tmp/hinge-roles

python3 integrations/transferable_roles/cli.py transfer role-synthetic-crm-followup-20260904 \
  --from-session session-A --to-session session-B --to-harness claude-tenon \
  --store /tmp/hinge-roles

python3 integrations/transferable_roles/cli.py export role-synthetic-crm-followup-20260904 \
  --store /tmp/hinge-roles

python3 integrations/transferable_roles/test_roles.py
```

## Access route shape (shared with C1/G2)

Routes reference `integrations/gemini_slack/peer_tool_gateway.py` fields:
`submit` / `status` / `events` / `recover`. This module does **not** edit that
gateway or `integrations/claude_headless/`.

Service tags come from `ground/SLACK_SERVICE_TAGS.json` (Notion/MagicPath peer
notes already recorded by GOAT).
