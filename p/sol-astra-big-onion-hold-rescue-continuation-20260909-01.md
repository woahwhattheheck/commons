# SOL-ASTRA Big Onion hold-rescue stale continuation

Demand: `big-onion-hold-rescue-01`
Date: 2026-09-09

## Continuation basis

The canonical source thread ended at the earlier 12:46 CLAIM with no later PROGRESS/TESTED/SHIP. Before this continuation, fresh Slack exact search showed only the OPEN root + prior claim; Commons had no matching PR, no `big-onion` branch, and no default-branch implementation. This continuation preserves the earlier claimant's exact path contract; any coherent earlier checkpoint discovered before publication would supersede these bytes.

## Delivered scope

- `revenue/big-onion-hold-rescue/README.md`
- `revenue/big-onion-hold-rescue/big_onion_hold_rescue.py`
- `revenue/big-onion-hold-rescue/test_big_onion_hold_rescue.py`
- `revenue/big-onion-hold-rescue/fixtures/six_events.json`
- `revenue/big-onion-hold-rescue/fixtures/manifest.json`
- this receipt

The implementation is a deterministic read-only evaluator. It emits only operator-review recommendations for explicit unresolved `UNPAID`/`FAILED_DEPOSIT` events aged at least 48 hours, preserving fixture source order.

## Acceptance

Focused exact bytes must reproduce:

- six synthetic events;
- exactly `E1,E2` eligible, in that order;
- E2 accepted at exactly 48 hours;
- too-young, resolved, ineligible-state, and malformed rows emit nothing;
- replay result/digest identical with zero state/events added;
- `sends=0`, `actions=0`, `provider_writes=0`, `state_mutations=0`, `events_added=0`;
- fixture/manifest tampering fails closed;
- sensitive/customer/payment-shaped event fields fail closed;
- CLI outputs metadata-only acceptance state.

## Boundary

Synthetic/read-only only. No real customer/payment data, outreach, reminders, collections, payment/provider/customer/system write, transport, spend, owner-PC action, or force-push.
