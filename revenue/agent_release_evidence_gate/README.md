# Agent Release Evidence Gate

A buyer-independent, deterministic **pre-effect admission control** for agent tool operations. It converts one proposed tool action plus current control-plane evidence into a content-addressed `RELEASE` or `HOLD` receipt.

This is designed for enterprises that already have agents, tools, approvals, and CI/evaluation systems but need one narrow answer before an effect crosses the boundary: **is this exact action still authorized, for this exact target and payload, against fresh evidence, right now?**

## What the gate binds

The request fingerprint covers the tool, operation, declared effect class, target, canonical payload, and payload hash. A release requires all of the following at the trusted evaluation clock:

- an exact capability match (`tool` + `operation` + `effect` + `target_prefix`);
- a payload hash that matches the canonical payload bytes;
- a snapshot inside its configured freshness window and not materially from the future;
- every required check present, `pass`, fresh, and bound to the exact request fingerprint;
- for configured `write` / `external` effects, an approved actor with an unexpired approval bound to the same request fingerprint;
- no prior committed effect for the exact request;
- remaining per-effect budget.

`RELEASE` is deliberately short-lived. `release_expires_at` is the earliest of the decision TTL, snapshot freshness boundary, check freshness boundaries, and approval expiry. A consumer must reject a receipt after that timestamp and must not reinterpret it as durable authority.

## Authority boundary

The gate **does not** execute a tool, mint credentials, prove provider state, settle a payment, sign a contract, establish policy compliance, or authorize later reuse. Its input evidence is only as authoritative as the systems that produce it. A production wrapper should source policy, checks, completed-effect history, and approvals from authenticated systems and call `evaluate()` with a trusted UTC clock at the actual execution boundary.

The CLI intentionally has no `--now` / caller-clock override. Tests inject a fixed trusted clock directly into `evaluate()` for reproducibility.

## Run the exact local gates

```bash
cd revenue/agent_release_evidence_gate
python -m unittest -v test_gate.py
python acceptance.py
python -m py_compile gate.py acceptance.py test_gate.py
```

Current acceptance fixture covers one valid release plus seven hostile states: stale snapshot, missing approval, stale check, hostile target, duplicate effect, zero effect budget, and wrong approval scope. The unit suite adds malformed/future clocks, failed/missing checks, payload drift, invalid approvals, duplicate ledger identifiers, and receipt determinism.

## Integration shape

A production adapter needs four edges:

1. **Request normalizer** — build the exact request object and canonical payload hash.
2. **Evidence collector** — fetch current checks and committed-effect ledger from authoritative stores.
3. **Approval resolver** — provide scoped actor approval with issue/expiry times.
4. **Effect wrapper** — evaluate immediately before the effect, reject HOLD/expired RELEASE, execute at most once, then durably append the committed effect receipt.

The gate itself stays network-free and side-effect-free, making it easy to run in CI, an agent gateway, a Slack approval worker, or a release controller.

## Commercial packaging (internal proposal, not booked revenue)

- **Synthetic proof — USD 2,500 one-time.** One buyer-approved action boundary, one fixture set, exact HOLD/RELEASE matrix, replay receipt, and implementation map. No production credentials required.
- **Single-boundary integration — USD 12,000 one-time.** One existing agent/tool boundary, authenticated evidence adapters, approval binding, committed-effect ledger, deployment/runbook, and buyer-owned acceptance suite.
- Production hosting, multi-boundary rollout, provider-specific security/compliance claims, on-call support, and autonomous external actions are separately scoped.

These are proposed internal list prices, not a market-rate claim, customer commitment, invoice, sale, or collected cash.
