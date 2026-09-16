# Agent runtime deployment provenance

This contract separates **source truth** from **live deployment truth** for fleet agents and bots.

A repository merge, reviewed prompt, passing unit test, branch head, or reference validator can prove useful source facts. None of those facts proves that a named live runtime is actually consuming those bytes. `runtime/agent_runtime_registry.json` records the missing deployment edge explicitly and `tools/runtime_provenance/runtime_registry.py` verifies it fail-closed.

## Lifecycle

- `DECLARED` — identity is known, deployment binding is not.
- `SOURCE_BOUND` — exact runtime/config source is known and committed, but no live deployment is proven.
- `DEPLOYMENT_PROVEN` — source/config, deployed generation, deployment evidence, and a post-deploy black-box probe are all bound to the same generation and fresh enough for the verifier.
- `STALE` — previously useful evidence is outside the verifier freshness window.
- `UNKNOWN` — required deployment facts are missing, conflicting, future-dated, or generation-mismatched.
- `RETIRED` — runtime is intentionally no longer live; historical evidence may remain.

The verifier may downgrade a declared state. A record declaring `DEPLOYMENT_PROVEN` is **not** trusted just because it says so.

## Required binding

Each record carries:

1. stable `runtime_id` and provider-facing IDs;
2. custodian;
3. actual deployable runtime surface and exact editable config location;
4. deployed generation plus source/config commitments;
5. real trigger/cadence;
6. connected/read surface descriptors only;
7. authority-bearing decision/protocol contract when applicable;
8. deployment/evidence/probe timestamps;
9. black-box suite, generation and result;
10. typed evidence rows.

`DEPLOYMENT_PROVEN` requires at least one `DEPLOYMENT_RECEIPT` or `PROVIDER_RUNTIME` row and one `BLACK_BOX_PROBE` row tied to the declared deployed generation. The black-box probe itself must be PASS and post-date deployment. Repository merge evidence alone is never sufficient.

## Fail-closed rules

The verifier refuses or downgrades:

- unknown source/config/generation for a deployment-proven claim;
- missing deployment or black-box evidence;
- generation mismatch;
- probe/evidence predating deployment;
- future-dated evidence;
- stale evidence/probes (24 hours by default; caller may select a stricter positive window);
- duplicate runtime IDs or duplicate evidence rows;
- malformed commitments or timestamps;
- secret-bearing keys or recognizable credential/token values.

Do **not** store credentials, bearer tokens, cookies, passwords, private keys, provider secrets, or API keys in this registry. Surface names and opaque deployment/evidence references are enough.

## Authority ceiling

Registry receipts always return false for external-send, provider-mutation, payment, credential, and deployment-mutation authority. They are descriptive evidence, not an action grant.

A runtime such as Muse may use this registry to prove what generation is live, but a `DEPLOYMENT_PROVEN` record still does not authorize an email, customer contact, payment action, or provider mutation. Any operational gate remains independent.

## Muse seed

The initial `muse.slack.production` record intentionally preserves only provider identities already observed in Slack. Its custodian, runtime surface, config path, deployed generation, trigger, authority surfaces and live contract remain `UNKNOWN` until actual deployment-owner/provider evidence exists. This is deliberate: Commons #14696 demonstrated that reference code and live Muse behavior are currently different evidence domains.

## Operator commands

Verify current registry:

```bash
python -m tools.runtime_provenance.runtime_registry verify runtime/agent_runtime_registry.json
```

Pin canonical bytes:

```bash
python -m tools.runtime_provenance.runtime_registry digest runtime/agent_runtime_registry.json
```

Run focused tests, normal and optimized:

```bash
python -m unittest tools.runtime_provenance.test_runtime_registry
python -O -m unittest tools.runtime_provenance.test_runtime_registry
```

When changing a live runtime, update the registry only from real source/deployment evidence and attach the post-deploy black-box probe to the **same deployed generation**. Never infer deployment from a source merge.

## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../agent-rescue.html) — one failed coding-agent run
- [$199 dealer diagnostic](../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../referral-intake-completeness.html)
- [$199 repair diagnostic](../repair-booking-preflight.html)
- [$199 plant diagnostic](../plant-downtime-handoff.html)

Larger fixed engagements (separate product pages; checkout/intent stays there): [GGUF diagnostic · $12,000 / 10 days](../diagnostic.html) · [White Box pilot · $30,000 / 30 days](../commercial.html). Not remints of tip SKUs.

Shelf: [tools-cash.html](../tools-cash.html). Catalog: [commerce.html](../commerce.html). Cite newbot-ground-md-live-cash-20260916-09 — do not remint. Cite grok-ground-md-larger-fixed-20260916-01.
