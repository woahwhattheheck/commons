# forge-equipment-newcomer-road-proof-20260905-01

## Claim
Owner credential-parity demand (coordination 2026-09-05): after capability-manifest discovery (#8813 / `cb1c443`), verify a newcomer can invoke one read and one reversible mutation on the shared equipment road without receiving raw secret bytes.

Direct vault retrieval remains Equipment-governor work. This slice proves the brokered road.

## Mechanism
Hermetic `test_shared_equipment_newcomer_road.py`:
- Stub Slack opener + gh runner (synthetic token never appears in tool results).
- Newcomer-labeled peer: `slack_read_channel` (read) + `github_create_branch` (reversible mutation).
- `build_capability_manifest(peer=...)` identical across peer labels.
- `redacted()` still strips `bot_token` fields.

## Not in this slice
Credential remint, owner-PC residents, HINGE R4, LotLens, #8802, Stripe.

## Verify
```bash
python -m unittest -q test_shared_equipment_newcomer_road.py
```

## Hands off
#8802 forever.
