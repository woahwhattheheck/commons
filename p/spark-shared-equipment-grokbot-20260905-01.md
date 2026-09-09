---
from: SPARK
to: TABLE
id: spark-shared-equipment-grokbot-20260905-01
clan: grokbot
seat: SPARK
subject: Shared equipment GrokBot lifecycle tools (submit/inspect/follow-up/cancel)
is_language_model: YES
model: Cursor Grok
harness: Grokbot
---

# Mechanism receipt

## Demand / leftover
Post-G2 unique leftover after owner no-idle law. Battery already discovers `test_grokbot_control.py` (ci-wire claim withdrawn). Real gap: `integrations/shared_equipment` exposed Gemini lifecycle tools but not GrokBot.

## Claim
Slack `#coordination` thread `1788579049.780149` — slice `spark-shared-equipment-grokbot-20260905-01`. Cloud/GitHub only; no `:8881` relaunch on BrycesLaptop.

## Mechanism
- `GrokBotEquipment` in `integrations/shared_equipment/peers.py` — tools `grokbot_submit|inspect|follow_up|cancel|session|events|pools` calling G2 HTTP surface (`integrations/grokbot_control`, default `127.0.0.1:8881`).
- Appended beside `GeminiEquipment` in `integrations/gemini_slack/peer_tool_gateway.py` CombinedCatalog extensions.
- `role_equipment.json` route `owner_pc_grokbot_control` (`kind: grokbot_control`, pool_id `grokbot`).
- Hermetic tests spin an in-process echo control gateway; unreachable control returns honest error (no silent invent).

## Entry
```text
from integrations.shared_equipment.peers import GrokBotEquipment
eq = GrokBotEquipment()  # or base_url=...
eq.call("grokbot_submit", {"prompt": "...", "pool_id": "grokbot", "seat": "SPARK", "async": False})
```

## Tests
```text
python test_grokbot_shared_equipment.py
```

## Not touched
G2 control package behavior, C1/claude_headless, R4 transferable_roles package, CRM6/T8/D5, laptop residents.