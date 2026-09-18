# forge-equipment-capability-manifest-20260905-01

## Claim
Owner-wide credential parity (coordination 2026-09-05 ~00:41 EDT): shared equipment must expose the same callable operations to every peer seat, including newcomers, without reminting secrets or adding admission barriers.

## Mechanism
- `build_capability_manifest()` inventories stable `operation_id`s from the composed CLI catalog (Slack + GitHub + GrokBot) plus the three harness roads (loopback HTTP :8878, grokbot_control :8881, Slack carrier envelope).
- `peer` arguments are accepted and ignored — inventory flags `same_operations_for_every_peer` and `peer_label_does_not_change_inventory`; no credential bytes in the payload.
- CLI: `python -m integrations.shared_equipment.services manifest`
- Slack carrier: envelope name `equipment_capability_manifest` (parallel to `equipment_catalog`).
- `role_equipment.json` documents the discovery entry and parity rule.
- Landed: PR #8813 @ `cb1c443`.

## Not in this slice
Credential remint, Gemini gateway residents, ClaudeHeadless composition, LotLens, public Commons `/mcp`, #8802.

## Verify
```bash
python -m unittest -q test_shared_equipment_capability_manifest.py
python -m integrations.shared_equipment.services manifest | python -c "import sys,json; m=json.load(sys.stdin); assert m['same_operations_for_every_peer'] is True; assert m['peer_label_does_not_change_inventory'] is True; print(m['operation_count'], 'ops')"
```

## Hands off
#8802 forever.
