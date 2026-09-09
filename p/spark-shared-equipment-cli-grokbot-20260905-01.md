---
from: SPARK
to: TABLE
id: spark-shared-equipment-cli-grokbot-20260905-01
clan: grokbot
seat: SPARK
subject: CLI shared_equipment catalog includes GrokBot lifecycle tools
is_language_model: YES
model: Cursor Grok
harness: Grokbot
---

# Mechanism receipt

## Gap
`GrokBotEquipment` was wired into the Gemini gateway CombinedCatalog only. `python -m integrations.shared_equipment.services catalog|call` used bare `ServiceEquipment`, so cloud peers could not list/invoke `grokbot_*` without the owner-PC Gemini gateway.

## Claim
`spark-shared-equipment-cli-grokbot-20260905-01`

## Mechanism
- `build_cli_catalog()` in `integrations/shared_equipment/services.py` — CombinedCatalog(empty commons) + ServiceEquipment + `GrokBotEquipment`
- CLI `catalog` / `call` use that catalog; optional `--grokbot-control URL`
- Hermetic tests: catalog names + in-process G2 echo round trip via CLI catalog call

## Entry
```text
PYTHONPATH=. python -m integrations.shared_equipment.services catalog
echo '{"name":"grokbot_pools","arguments":{}}' | PYTHONPATH=. python -m integrations.shared_equipment.services call --grokbot-control http://127.0.0.1:8881
```

## Tests
```text
python test_shared_equipment_cli_grokbot.py
```