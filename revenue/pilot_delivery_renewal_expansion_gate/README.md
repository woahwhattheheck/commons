# Pilot delivery → renewal / expansion owner-review gate

Issue: `#15155` / `PILOT-DELIVERY-TO-RENEWAL-EXPANSION-GATE-20260916-ZSOL`.

This package fills the stage **before** the already-landed
`revenue/paid_outcome_expansion_rail/**`.

The older paid-outcome rail requires a fresh buyer-authored `RENEWAL_REQUEST` or
`EXPANSION_REQUEST` and an exact owner-approved catalog revision before emitting
`RENEWAL_READY` / `EXPANSION_READY`. This package deliberately does **not**
manufacture that signal. It answers a narrower earlier question:

> Is the completed paid pilot internally coherent enough for a human owner to
> review renewal/expansion possibilities without pretending that the buyer has
> expressed interest or approved anything?

Its strongest state, `READY_FOR_RENEWAL_REVIEW`, is therefore upstream of the
older rail and cannot be substituted for it.

## Evidence chain

The compiler binds one exact commercial lineage and rechecks it from raw evidence:

1. accepted commercial baseline generation, currency, amount and scope digest;
2. strictly generated change-order lineage, with only `APPROVED` deltas changing
   the current commercial generation/economics;
3. every delivery milestone bound to that exact current commercial generation
   and explicitly `BUYER_HUMAN_ACCEPTED`;
4. final payment evidence for that same generation from
   `PROVIDER_SETTLEMENT` or `BANK_SETTLEMENT` — invoices, payment links and
   advertised amounts can never establish payment;
5. fresh support findings;
6. the explicit renewal-review window;
7. security/data gaps;
8. optional expansion hypotheses, which must remain
   `PROPOSED_NOT_ACCEPTED` and may not claim buyer interest, ROI, savings,
   usage, urgency or approval;
9. a route/collision/Muse identity for any later communication. The route is
   only retained context here; this module never performs arbitration or sends.

The deterministic terminal states are:

- `READY_FOR_RENEWAL_REVIEW`
- `HOLD_ACCEPTANCE`
- `HOLD_PAYMENT`
- `HOLD_WINDOW`
- `HOLD_EVIDENCE`
- `DNR`

`DNR` is terminal for an exact route. `READY_FOR_RENEWAL_REVIEW` means only
owner review is supportable. A later external touch still needs a fresh
collision census, Muse single-writer election and a separate send-capable
adapter. A genuine buyer signal can then be evaluated by the existing
paid-outcome expansion/renewal rail.

## Truth and authority boundary

Every receipt hard-codes `false` for:

- external send;
- Muse election;
- contract/signature;
- buyer acceptance establishment;
- buyer renewal or expansion interest;
- renewal/expansion approval;
- invoice authority;
- payment movement;
- cash/revenue recognition;
- deployment;
- scheduling;
- CRM mutation.

Delivery/merge is never treated as buyer acceptance. Invoice/payment-link
existence is never treated as settlement. No output infers ROI, savings, usage,
urgency, renewal interest or expansion approval.

## Source/currentness discipline

JSON is strict: duplicate keys, floats/non-finite values, bool-as-int aliases,
unknown fields, bad hashes, unsafe source URIs, generation gaps and future
timestamps fail closed.

Current compilation owns process UTC. Evidence freshness is code-bounded:
payment 90 days, support/security/hypothesis evidence 90 days, milestone
acceptance 366 days, and route-control evidence 7 days. Receipt verification
first checks exact receipt integrity and then recompiles against the current
process clock; a historically READY receipt cannot revive stale or closed-window
state.

The SHA-256 receipt digest is an integrity digest, not a signature or proof of
provider identity.

## Run

```bash
python -m unittest -v revenue.pilot_delivery_renewal_expansion_gate.test_gate
python -O -m unittest -v revenue.pilot_delivery_renewal_expansion_gate.test_gate
python -m py_compile \
  revenue/pilot_delivery_renewal_expansion_gate/engine.py \
  revenue/pilot_delivery_renewal_expansion_gate/test_gate.py
```

Current-state CLI:

```bash
python -m revenue.pilot_delivery_renewal_expansion_gate.engine \
  compile revenue/pilot_delivery_renewal_expansion_gate/demo/synthetic_ready.json \
  --output /tmp/renewal-review-receipt.json

python -m revenue.pilot_delivery_renewal_expansion_gate.engine \
  verify revenue/pilot_delivery_renewal_expansion_gate/demo/synthetic_ready.json \
  /tmp/renewal-review-receipt.json
```

The checked-in fixture is synthetic. It encodes no customer, buyer, provider,
payment, renewal, expansion or revenue fact.
