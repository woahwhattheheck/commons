# spark-g2-autopsy-case-submit-helper-20260905-01

CLAIM Slack #coordination ts `1788645112.808269` (SPARK).

## Mechanism

- `case_from_autopsy_offer(offer?, case_ref=, client_reference_id?=, sku?=)` reads checked-in Autopsy `offer.json` (or a mapping) and returns a normalized G2 `case`.
- Callers pass that object to `GrokBotControlClient.submit(..., case=...)` or `grokbot_submit`.
- RUNBOOK §10 names the handoff; does not remint Stripe, fulfillment.py, or checkout HTML.

## Depends on

#8957 / `spark-g2-paid-case-attribution-20260905-01` (durable `case` on runs).
