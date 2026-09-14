# Right-now checkout currentness

`revenue/agent_failure_autopsy/offer.json` records historical Stripe identity and
integrity evidence for the USD 29 Agent Failure Autopsy. Historical evidence is
not enough to authorize the word **current**.

The canonical `host/right_now_revenue.py` path now requires two independent
layers before `truth.active_chargeable_checkout` can remain `true`:

1. the frozen historical checkout contract still reconciles the offer, account,
   product, price, Payment Link, amount, public checkout URL, and retained offer
   receipt; and
2. `stripe_checkout_current.json` is an exact code-pinned, minimized readback
   from authenticated Token Junkie Labs **live-mode Stripe GETs**.

The retained current readback binds:

- Stripe account `acct_1U6HI9ATH4EDE7XD`;
- Payment Link `plink_1UCFbLATH4EDE7XDlTunr6iO`, active/live and exact public URL;
- price `price_1UCFbHATH4EDE7XD4NNrjfUe`, active/live;
- product `prod_VCevsvv7skWk3e`;
- USD 29 one-time amount and quantity 1;
- the `agent-failure-autopsy-29` / `commons-agent-failure-autopsy-offer/v1`
  metadata binding; and
- the UTC time at which those provider objects were read.

## Currentness rule

Production currentness uses **process-owned UTC only**. The catalog's `as_of`
field is historical source metadata; changing or backdating it cannot extend the
provider evidence lifetime.

A retained provider readback authorizes current checkout truth for at most
**24 hours** after `observed_at_utc`. Future observations, stale observations,
inactive/revoked link or price state, test-mode objects, identity/amount/
metadata drift, unexpected provider operation provenance, or any retained-file
byte change fail closed.

Refreshing currentness requires a new authenticated read-only Stripe retrieval
and a reviewed update of the retained readback plus its code-pinned SHA-256.
Do not copy forward the old timestamp.

## Authority ceiling

This mechanism is read-only truth custody. It does **not** create or update a
Payment Link, charge or refund a buyer, infer that anyone purchased, accept a
scope, contact a buyer, or recognize cash/revenue. `active_chargeable_checkout`
means only that fresh provider evidence shows the exact public checkout is
currently chargeable under the pinned offer contract.

The pre-fix compiler is retained as `host/right_now_revenue_core.py` so
historical replay/integrity behavior remains reviewable. The canonical wrapper
adds current provider authority without converting replay inputs into a
caller-selected production clock.
