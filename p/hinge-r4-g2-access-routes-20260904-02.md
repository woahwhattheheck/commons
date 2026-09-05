# HINGE R4 ↔ G2 access_routes align

- Slice: `hinge-r4-g2-access-routes-20260904-02`
- Claim: `#coordination` ts `1788570388.918329`
- Parent R4: PR #8760 / merge `217aa69`
- G2 source: SPARK PR #8761 / `5154aa8f` — `integrations/grokbot_control/` @ `http://127.0.0.1:8881`

## What changed

- Fixture + README carry `kind: grokbot_control` route (`pool_id`, HTTP map, client path).
- `roles.py` preserves G2 route fields; occupant may carry `seat` (seat ≠ role_id).
- Tests assert G2 route shape; no edit to `integrations/grokbot_control/*`.

## Not touched

SPARK/LEDGER/QUILL/FORGE/TENON/MICA lanes. Commons `/mcp` KEEP. No remint.
