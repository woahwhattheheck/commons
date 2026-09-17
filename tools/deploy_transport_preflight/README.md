# Deploy transport source-binding preflight

This tool answers one narrow question **before** a hosting mutation: does the declared provider action surface have a machine-readable path that can carry the exact immutable source generation we intend to deploy?

It exists because “create a project” or “deploy a site/current project” is not the same thing as binding the intended repository bytes. A provider connector can be perfectly capable of creating infrastructure while still being unable to prove which source generation it will publish.

## Outcomes

- `READY_SOURCE_BOUND_PATH` — at least one declared action can bind an immutable repository commit, artifact digest, file-bundle digest, source-generation ID, or an existing project whose retained planning binding exactly matches the request.
- `HOLD_SOURCE_UNBOUND` — actions may create/deploy infrastructure, but none can mechanically bind the requested source generation.
- `HOLD_AMBIGUOUS_CAPABILITY` — the action manifest is semantically unknown, contradictory, or names a different provider.

The report always keeps `provider_authenticated`, `project_create_authorized`, `deploy_authorized`, `public_url_proven`, `competition_submission_authorized`, and `payment_or_revenue_proven` false. This is a deterministic planning compiler, not provider authentication or deployment authority.

## Source identity rules

A mutable branch name is never sufficient. Repository binding requires `repo` plus a lowercase 40-hex immutable `commit_sha`. Artifact and file-bundle paths use lowercase SHA-256. A project-ID deploy path is READY only when a separate retained project-binding record matches provider, project, and the complete immutable source identity. Free-form prose, URLs in descriptions, project names, and site IDs do not become source bindings by implication.

The request, capability manifest, optional project binding, and compiled report use strict canonical JSON. Duplicate keys, floats/nonfinite numbers, unsafe integers, lone surrogates, unknown schema fields, unsafe paths, noncanonical repository URLs, and receipt tampering fail closed. `verify` recompiles the entire report from the inputs.

## Current-provider fixtures

`fixtures/netlify_current.json` models the connector surface observed on 2026-09-17: create-by-name/team plus deploy-existing-site. Without an exact retained project/source binding, the fixture returns `HOLD_SOURCE_UNBOUND`.

`fixtures/vercel_current.json` models deploy-current-project. With no exact project/source binding, it also returns `HOLD_SOURCE_UNBOUND`.

These fixtures are **caller-retained planning evidence**, not authenticated provider facts. Re-census the real provider before any mutation.

## CLI

```text
python tools/deploy_transport_preflight/preflight.py compile \
  --request request.json --manifest manifest.json [--binding project-binding.json] \
  --out report.json

python tools/deploy_transport_preflight/preflight.py verify \
  --request request.json --manifest manifest.json [--binding project-binding.json] \
  --report report.json
```

`compile` creates the report exclusively and refuses to overwrite an existing path.

## Proof

```text
python -m unittest tools.deploy_transport_preflight.test_preflight
python -O -m unittest tools.deploy_transport_preflight.test_preflight
python -m py_compile tools/deploy_transport_preflight/preflight.py tools/deploy_transport_preflight/test_preflight.py
```

The hostile suite covers the two current unbound provider shapes, positive immutable repo/artifact/bundle paths, exact existing-project matching, cross-provider/project/source transplant, branch-only input, unknown/contradictory action semantics, strict JSON hazards, canonical repository URLs, report tamper, CLI compile/verify, and create-exclusive output.

## Authority ceiling

This tool performs no provider mutation. A READY result is only evidence that a declared transport surface has a machine-readable source-binding path. It is not evidence of current provider authentication, deployment, a live URL, competition submission, prize eligibility, payment, cash, or revenue.
