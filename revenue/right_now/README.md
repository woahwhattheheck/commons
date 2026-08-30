# Right-now revenue control tower

This lane turns the existing offer catalog, payment receipt, smart-outreach
evidence, and canonical collision receipts into one deterministic execution
queue. It is deliberately larger than a new SKU: it joins what Commons can
sell, who has evidenced pain, what must not be resent, what can happen next,
and which external fact still blocks cash.

The compiler reads six canonical public sources and every canonical outreach
suppression receipt. It validates prices against their owner catalogs, keeps
cash/payment/reply/acceptance facts separate, reuses Smart Outreach's measured
qualification decisions, ranks the work queue, and emits SHA-256 receipts for
every directly composed source.

```sh
python3 host/right_now_revenue.py compile
python3 host/right_now_revenue.py validate
python3 host/gpt_action_packets.py validate
python3 host/gpt_action_packets.py next
python3 -m unittest test_right_now.py test_right_now_execution.py test_smart_outreach.py test_gpt_action_packets.py
```

Buyer-facing first rung: [agent-triage.html](../../agent-triage.html).
Canonical $199 terms: [diagnostic_offer.json](./diagnostic_offer.json).
GPT packets: [action_packets.json](./action_packets.json).
Demand ledger: [demand_ledger.json](./demand_ledger.json).
Experiments: [experiments.json](./experiments.json).

`control.json` is the committed browser projection. `validate` fails whenever
the projection drifts from its sources, including a price, cash, payment,
candidate, collision, or hash change. `right-now.js` renders that exact snapshot
without creating a second ledger.

## Truth boundary

The control tower performs zero contact, transport, payment, acceptance, or
delivery actions. `READY_TO_DRAFT` is not authorization to send. An intake is
not payment, a payment event is not cash until evidenced, and a public quote is
not buyer acceptance. Missing external facts stay explicit blockers rather
than being promoted into progress.

## Operator loop

1. Land first-party demand evidence in Smart Outreach.
2. Rerun its planner and preserve every collision / do-not-resend receipt.
3. Compile this control snapshot.
4. Work the highest-ranked non-held queue item.
5. Record the real external event in its owner ledger.
6. Recompile; never hand-edit `control.json` into a better state.

Longer-horizon NOW, SOON, and LATER routes remain in the catalog and on the
commerce page. This control plane changes execution order, not ambition.
