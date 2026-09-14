# Agent Tool-Call Evidence Gate

A deterministic preflight boundary for agentic systems that can cause side effects. The gate answers one narrow question before an external mutation: **does this exact request satisfy the buyer's current policy and replay/budget/rate evidence?** It never executes the tool call itself.

## Contract

Inputs are a closed policy, one closed request envelope, and the previous append-only allow ledger. A request binds agent/version, actor/role, tool/action, target resource, data class, optional human approval evidence bound to the exact call-intent digest, idempotency key, request budget, authoritative rate-window identity, and trace evidence. The output is exactly `EXECUTE_ALLOWED` or `HOLD`, stable sorted reason codes, a policy/request/ledger evidence manifest, and a receipt digest.

Only `EXECUTE_ALLOWED` appends a ledger row. A HOLD is state preserving. Replaying an idempotency key or previously allowed request ID, crossing per-request/window budget or rate ceilings, using a stale-policy ledger, mutating a ledger digest, restricted-data exposure, missing required human approval, agent/version mismatch, or role/resource mismatch fails closed. The gate's authority string is deliberately `TOOLCALL_PREFLIGHT_ONLY_NO_PROVIDER_MUTATION_AUTHORITY`.

The `window_id` must be supplied by the trusted host scheduler/runtime (for example a UTC hour bucket). A hostile agent must not be allowed to choose fresh window IDs to evade rate limits. Likewise, approval evidence must come from the buyer's approval system; its `intent_sha256` must equal the gate's digest of the exact request identity, agent/version, actor/role, call/resource/data class, idempotency key, budget, trusted window and trace evidence. The gate does not invent human approval.

## Golden acceptance

```bash
python -m unittest discover -s products/agent_toolcall_evidence_gate/tests -v
python -O -m unittest discover -s products/agent_toolcall_evidence_gate/tests -v
python -m products.agent_toolcall_evidence_gate.acceptance
```

The synthetic golden fixture has exactly 240 envelopes: 192 valid and 48 defective, eight each for disallowed tool/action, role-resource mismatch, restricted-data exposure, missing human approval, budget/rate breach, and replay/idempotency collision. Required result: `192 EXECUTE_ALLOWED / 48 HOLD`, zero defective calls allowed. This is mechanism evidence, not buyer production evidence.

## CLI

`python -m products.agent_toolcall_evidence_gate.cli evaluate policy.json request.json ledger.json --receipt receipt.json --next-ledger ledger.next.json`

A HOLD exits 2; an allow exits 0. `verify` deterministically replays a transition and fails if the receipt or next ledger was transplanted or modified.

## Commercial package

`offer.json` positions a fixed **$15,000 / 10-business-day** pilot for one agent/tool side-effect boundary, up to ten policy rules, a runtime adapter, replay/budget/rate ledger integration, acceptance fixtures and handoff. This is seller positioning only: no buyer acceptance, contract, payment, provider configuration, provider mutation, or recognized revenue is represented by this source package.

The product originated from a Travelers demand signal, but the implementation is generic and contains no Travelers data or assertion that Travelers is procuring it.
