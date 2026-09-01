# Vercel aggregate deployment-capacity activation — 2026-09-01

Status: **ACTIVATION RECEIPT**

Selected resource: `vercel`

Transition: `LIVE / REACHABLE / CONSTRAINED → LIVE / PRODUCING / CONSTRAINED`

Concrete consumer: Commons Queue Manager and deployment routers deciding whether a current Vercel project road exists.

## Measured outcome

- Authenticated Vercel team enumeration succeeded.
- One team exists on the Hobby plan.
- Project enumeration returned zero projects.
- The deterministic routing result is `NO_PROJECT_READY` with zero ready deployment routes.
- Deployment enumeration was not attempted because deployments are project-scoped; `deployments_observed` is `null`, not a fabricated zero.
- Team name, slug, ID, and all private account/project identifiers are excluded.

## Product

- `host/vercel_capacity_inventory.py` builds or checks the fail-closed aggregate.
- `inventory/resources/vercel_capacity.json` is the public-safe consumer surface.
- `test_vercel_capacity_inventory.py` locks identifier exclusion, deterministic output, project/deployment sequencing, and zero-project truth.

## Exact state

Connector observation Commons main: `5abd1b8259cbb307c33e3e9cbcfc810a36585c92`

Activation base main: `31503d4fc00ae2be15c5bb4381c504eb3fbcb831`

Connected-app aggregate: 13 automations; six enabled and seven disabled/excluded from capacity.

## Verification

- 11/11 focused tests passed.
- Python compile passed.
- Deterministic real-input projection returns one team, zero projects, and `NO_PROJECT_READY`.
- The six-path collision audit is disjoint from all eight open ChartTrace/LIMS PRs and recent CCC/BLINK work.
- No account identifier, secret, environment value, domain, auth gate, network client, subprocess, or provider mutation is present in the product.

## Boundaries

A connected Vercel team is live account capacity, not a deployable project. Zero projects does not mean zero account capacity. No deployment, project/config/environment/domain mutation, access-link creation, provider spend, device action, Grok/Cursor/Claude use, Titan mutation, outreach, resend, payment, revenue, or cash occurred. The projection expires after seven days or the next team/project change.
