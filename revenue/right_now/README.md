# Right-now revenue control tower

This lane turns the existing offer catalog, payment receipt, smart-outreach
evidence, settled-award evidence, and canonical collision receipts into one
deterministic execution queue. It is deliberately larger than a new SKU: it
joins what Commons can sell, who has evidenced pain, what must not be resent,
what has actually been paid, what can happen next, and which external fact
still blocks cash.

The compiler reads canonical public sources and every canonical outreach
suppression receipt. It validates prices against their owner catalogs, keeps
cash/payment/reply/acceptance facts separate, reuses Smart Outreach's measured
qualification decisions, ranks the work queue, and emits SHA-256 receipts for
every directly composed source.

```sh
python3 host/settled_awards.py validate revenue/right_now/settled_awards.json
python3 host/settled_awards.py summary revenue/right_now/settled_awards.json
python3 host/right_now_revenue.py compile
python3 host/right_now_revenue.py validate
python3 host/gpt_action_packets.py validate
python3 host/gpt_action_packets.py next
python3 -m unittest test_settled_awards.py test_right_now.py test_right_now_execution.py test_smart_outreach.py test_gpt_action_packets.py
```

Buyer-facing first rung: [agent-triage.html](../../agent-triage.html).
Canonical $199 terms: [diagnostic_offer.json](./diagnostic_offer.json).
Settled awards: [settled_awards.json](./settled_awards.json).
GPT packets: [action_packets.json](./action_packets.json).
Send authorization ledger: [send_authorizations.json](./send_authorizations.json).
Demand ledger: [demand_ledger.json](./demand_ledger.json).
Experiments: [experiments.json](./experiments.json).

`control.json` is the committed browser projection. `validate` fails whenever
the projection drifts from its sources, including a price, cash, payment,
settled award, candidate, collision, or hash change. `right-now.js` renders that
exact snapshot without creating a second ledger.

## Settled-award boundary

`settled_awards.json` records sponsor-confirmed paid awards in their original
currencies. The validator rejects duplicate award IDs, duplicate idempotency
keys, non-canonical or non-positive amounts, malformed public references,
future payment dates, invented USD equivalents, availability promotion, and
repeat-collection instructions. Private receipt locators remain redacted.

A paid award is not automatically USD cash, bank availability, wallet custody,
or withdrawability. Currency totals stay separate, and the right-now control
continues to derive `collected_cash_usd` only from its existing USD payment
receipt. `NONE_DO_NOT_RESEND` is authoritative collection suppression, not an
instruction to contact the sponsor again.

## First-party send-authorization boundary

A packet cannot mint its own external-send authority. Any packet marked
`ready-to-send under existing authorization` must embed one exact record from
`send_authorizations.json`; the validator independently reads that canonical
ledger and requires the record to bind the exact candidate, exact public
contact route, SHA-256 of the exact proposed message, monotonically increasing
generation, issue/expiry window, and `confirm_before_send=true`.

Only the highest generation for one candidate+route is current. A later
`REVOKED` generation invalidates every older `LIVE` receipt, and the consumer
revalidates the packet and ledger again immediately before returning a send
instruction. Unknown fields, bool-as-integer generations, duplicate generation
claims, future issuance, expiry, cross-candidate reuse, route reuse, message
mutation, or an embedded receipt that differs from the canonical ledger all
fail closed.

The committed ledger starts empty. Therefore the current packet set has no
send-ready authority. Adding a row is an explicit owner-controlled evidence
mutation; it does not itself contact anyone, and the final one-time confirmation
remains required at consumption time.

## Truth boundary

The control tower performs zero contact, transport, payment, acceptance,
conversion, withdrawal, or delivery actions. `READY_TO_DRAFT` is not
authorization to send. An intake is not payment, a payment event is not USD
cash until evidenced as USD cash, and a public quote is not buyer acceptance.
Missing external facts stay explicit blockers rather than being promoted into
progress.

## Operator loop

1. Land first-party demand evidence in Smart Outreach.
2. Rerun its planner and preserve every collision / do-not-resend receipt.
3. Add sponsor-confirmed paid awards only through the strict settled-awards ledger.
4. Compile this control snapshot.
5. Work the highest-ranked non-held queue item.
6. Record the real external event in its owner ledger.
7. Recompile; never hand-edit `control.json` into a better state.

Longer-horizon NOW, SOON, and LATER routes remain in the catalog and on the
commerce page. This control plane changes execution order, not ambition.

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../../titanmcp.html). Cite Latch Pad KEEP.