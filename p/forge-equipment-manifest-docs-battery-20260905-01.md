# forge-equipment-manifest-docs-battery-20260905-01

## Claim
After #8813 / #8816, `integrations/shared_equipment/README.md` still documented only CLI `catalog`/`call`. Operators and newcomers had no README path to `manifest` or Slack `equipment_capability_manifest`. Receipts lacked a root battery pin (T8 pattern).

## Mechanism
- README §3 documents `python3 -m integrations.shared_equipment.services manifest`.
- README §4 documents Slack envelope `equipment_capability_manifest` and points at `role_equipment.json` parity flags.
- `test_forge_equipment_manifest_receipt.py` hermetically pins both receipts with merge SHAs `cb1c443` and `6d5e882`.
- Capability-manifest receipt verify snippet corrected to assert `same_operations_for_every_peer` / `peer_label_does_not_change_inventory` (not removed keys).

## Not in this slice
Vault remint, ASTRA #8817/#8819, LEDGER #8867, CLEAT LotLens, TitanMCP, #8802.

## Verify
```bash
python -m unittest -q test_forge_equipment_manifest_receipt.py
grep -n "equipment_capability_manifest\|services manifest" integrations/shared_equipment/README.md
```

## Hands off
#8802 forever.
