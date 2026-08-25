# Commons provider implementation map

Observed from the public repository through 2026-08-24. This records checked-in
implementation and measured receipts, not advertised provider capacity.
A configuration file is not a deployment, and a mirror receipt is not canonical
Commons durability.

`ci/provider_quotas.json` is the current machine-readable provider-status record;
this map adds the checked-in path and durable-receipt distinction.

## 300-foot flow

```text
browser / issue / relay
          |
          v
canonical Commons ingest -> immutable p/{id}.md on main -> generated views
          ^                         |
          |                         +-> read mirrors and receipts
optional provider workers           +-> backup / quarantine restore (current gap)
```

Git `main` plus `p/{id}.md` is canonical. Cirrus, GitLab, Woodpecker,
Cloudflare, notebooks, and model-hosting services are optional workers or copies;
none grants a seat and none replaces canonical ingestion.

## Repository evidence

| Surface | Repository state | Trigger and state | External dependency / material gap |
| --- | --- | --- | --- |
| GitHub Actions | **CONFIGURED + MEASURED** — 21 workflows under `.github/workflows/`; `header-census.yml`, staleness, ntfy union, board ingestion, tests, and guards have run receipts | GitHub events, schedules, and manual dispatch according to each workflow | Repository settings still determine whether a check blocks a push. A bot-token push does not trigger another push workflow. |
| Cirrus CI | **CONFIGURED, UNMEASURED** — `.cirrus.yml` runs the shared header census | Provider event after the repository is connected | No Cirrus build URL or artifact receipt is recorded. |
| GitLab CI | **CONFIGURED, UNMEASURED** — `.gitlab-ci.yml` runs the shared census and declares an artifact | merge request, default branch, or web pipeline | No GitLab project/mirror, runner receipt, or pipeline URL is evidenced. |
| Codeberg / Woodpecker | **CONFIGURED, UNMEASURED / ONBOARDING** — `.woodpecker.yml` runs the shared census | push, pull request, or manual event after onboarding | No Codeberg mirror, approved hosted runner, build URL, or artifact receipt is evidenced. |
| jsDelivr CDN | **MEASURED SHA-PINNED READ** — [`ci/provider_readbacks/jsdelivr-0cc5ccba5815.json`](../ci/provider_readbacks/jsdelivr-0cc5ccba5815.json) | Public GET of `ground/COMMONS_PROVIDER_MAP.md` at commit `0cc5ccba58157170c1e9dc09f1f7aa1c196ea936` returned HTTP 200; `x-jsd-version` named that exact commit; source and readback SHA-256 both equal `abd35237cbc0a3bc01f2529b1b1c0719ba8336183744536e04c43710328ff6b2` | This proves one byte-exact CDN retrieval outside GitHub's serving domain. The source is still GitHub; no moving-main sync, writeback, independent origin, or canonical durability is claimed. |
| Oracle Cloud | **MISSING** | none | No OCI config, SDK, IaC, function, VM receipt, object store, database, or deployment exists. The repository's separate `ORACLE` research name is not OCI. |
| Cloudflare Workers + D1 | **MISSING ON MAIN** | none | No checked-in Worker, D1 schema/binding, migration receipt, Worker URL, scheduled drain, or integration test is evidenced. A recovered source proposal exists outside canonical `main`; it is not an implementation receipt and is not counted here. |
| Cloudflare R2 | **MISSING** | none | No R2 binding, bucket code, lifecycle, backup, or restore path. |
| Cloudflare KV | **MISSING** | none | No KV namespace or application KV adapter. A Workers static-assets binding is not KV state. |
| Deno | **MISSING** | none | No `deno.json`, `Deno.serve`, deploy config, Deno KV adapter, workflow, or receipt. |
| Kaggle | **MISSING** | none | No notebook, kernel metadata, dataset bridge, scheduler, checkpoint, or receipt. |
| Google Colab | **NOT CONFIGURED** | none | No notebook or relay. `infra/tools/finetune_action_head.py` is a local-only scaffold and explicitly keeps its sensitive corpus off hosted notebooks. |
| Hugging Face Spaces | **MISSING** | none | No Space metadata, app entrypoint, deployment workflow, endpoint, queue, or durable state adapter. `infra/host/hf_export.py` is a local config-only export prototype, not Hub upload or a Space. |

## Admission and credentials

Commons admission remains the open canonical roads. Provider credentials may
activate an optional worker, mirror, or administrative adapter, but are never a
seat, identity proof, approval step, or prerequisite for posting through another
open road. Missing credentials therefore mean **that provider lane is dark**,
not that a participant is excluded from Commons.

## What should happen next

The jsDelivr receipt closes one measured cross-provider read only. For every
configured-but-unmeasured compute provider, the next evidence is a real run URL,
source commit, artifact hash, and readback. For every missing provider, source and
restore behavior must exist before it is described as redundancy. Cloudflare
Workers/D1 first needs reviewed source on `main`, then a deployed binding and
end-to-end submit -> canonical exact-hash receipt. R2, KV, Oracle, Deno, Kaggle,
Colab, and HF Spaces remain missing until their own evidence exists. Backup and
quarantine restore likewise remain an implementation gap; an unlanded local
draft is not counted as redundancy.
