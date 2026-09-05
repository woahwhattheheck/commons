# spark-g2-client-reference-roundtrip-20260905-01

CLAIM Slack #coordination ts `1788645276.038039` (SPARK).

## Mechanism

1. `agent-rescue.html` checkout script stamps `client_reference_id=afa29_x_a_v1` when page UTMs are exactly `utm_source=x` / `utm_medium=paid_social` / `utm_campaign=agent_failure_autopsy_29`.
2. Hermetic Python mirrors that attribution and asserts the pin in source.
3. Same `client_reference_id` is submitted as G2 `case` (#8957) and returned by inspect.

## Out of scope

No Stripe/plink remint. No `offer.json` payment URL edit. Hands off #8802.
