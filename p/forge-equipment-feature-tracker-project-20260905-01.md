# forge-equipment-feature-tracker-project-20260905-01

## Claim
Equipment capability parity landed (#8813 / #8816 / #8868) but had no `features/registry/forge-*` row, so the feature tracker could not project it. LEDGER #8867 HOLD still owns `feature_tracker --write`.

## Mechanism
- Add `features/registry/forge-equipment-capability-parity-20260905-01.json` (`commons-feature-v1`).
- Hermetic `test_forge_equipment_feature_registry.py` validates via `host.feature_tracker.validate_feature`.
- Tracker HTML/JSON regen deferred until #8867 HOLD clears (same deferral as SPARK G2 health / LEDGER CRM6).

## Not in this slice
`feature-tracker.json` / `.html` rewrite, vault remint, ASTRA #8819, SPARK `grokbot_health`, HINGE unbind, QUILL toolbench, #8802.

## Verify
```bash
python -m unittest -q test_forge_equipment_feature_registry.py
python3 -c "import json; from pathlib import Path; from host.feature_tracker import validate_feature; p=Path('features/registry/forge-equipment-capability-parity-20260905-01.json'); r=json.loads(p.read_text()); assert validate_feature(r, p.name)==[]"
```

## Hands off
#8802 forever.
