# grok-incoming-models-keep-lift-20260916-01

Grok Build — KEEP-lift leftover incoming-models freeze after NEWBOT #14994.
Do not remint `newbot-incoming-models-html-keep-larger-fixed-20260916-19`.

## Measured leftover on current main after `b787e688`

1. `test_incoming_models_hub_payload_readback.py` KEEP froze living helper
   `host/incoming_models.py` at `7f4ae3bf` vs tip blob `108797f0` after #14994
   baked `#live-cash` + Larger fixed into `render_html`.
2. Same-cluster door `incoming-models.html` still froze leftover `ef42b9d5`
   vs TYPE #14975 tip blob `56aab207` (Larger fixed already on the door).
3. Rematch KEEP then needed a successor pin for the leftover readback test
   after that lift (`1fd96349` → `3d509221`).

## Ship

- Lift leftover helper KEEP `7f4ae3bf` → `108797f0`
- Lift leftover door KEEP `ef42b9d5` → `56aab207`
- Lift rematch leftover-test KEEP `1fd96349` → `3d509221`
- Hermetic regression `test_grok_incoming_models_keep_lift_20260916_01.py`
- Do not remint leftover unique-pack receipts, NEWBOT id, or tip HTML

Tip KEEP. Hands off #8802. 337 is not law. No invent Stripe. No PUT ingest.
