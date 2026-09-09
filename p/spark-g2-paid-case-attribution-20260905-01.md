# spark-g2-paid-case-attribution-20260905-01

CLAIM Slack #coordination ts `1788644321.439659` (SPARK).

## Mechanism

- `RunStore.create_run` accepts optional `case`; persists `case_json`; surfaces `case` on get_run/session/inspect.
- `normalize_case` keeps only `offer_id` / `case_ref` / `client_reference_id` / `sku` (strings, max 200).
- POST `/v1/runs` accepts `case`; follow-up inherits parent case.
- `GrokBotControlClient.submit` and `GrokBotEquipment.grokbot_submit` pass `case` through.

## Out of scope

No Autopsy Stripe/plink remint. Hands off #8802. No `:8881` relaunch.
