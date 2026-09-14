# WRI Open Timber Portal — proposal carrier

This package is a **pre-submission technical carrier** for World Resources Institute's September 2026 Open Timber Portal developer consultancy. It is deliberately not a bid sender and not a representation that Token Junkie Labs satisfies WRI's unknown vendor/experience gates.

## What is source-grounded

The buyer-owned public repository `https://github.com/wri/fti_api` identifies `fti_api` as the Ruby on Rails backend for Open Timber Portal, with a JSON API, admin interface, Sidekiq jobs, PostgreSQL/PostGIS, Redis, RSpec/parallel tests, and a documented EC2/Terraform/Capistrano deployment path.

Current secondary procurement mirrors agree that WRI issued an Open Timber Portal developer RFP in early September 2026 and describe five recurring activity buckets: reference/runtime updates, performance/security improvement, cross-surface fixes, ongoing maintenance/bugs, and a forward improvement list with bi-weekly WRI coordination. They also show an October start and March 31 delivery milestone. **They are not controlling procurement authority.**

The official WRI procurement page is recorded in the fixture but was HTTP-403 to the public retriever in this session, so it is intentionally assigned **zero factual claims** by the compiler.

## Why the carrier is held

Secondary indexes conflict on the formal Rails role label and even normalize the deadline differently. The current carrier therefore preserves seven blocking procurement unknowns:

- exact submission route;
- deadline time/timezone;
- mandatory qualifications;
- required forms/representations;
- evaluation method;
- pricing instructions;
- formal role title.

`TECHNICALLY_READY` means the source-bound six-month engineering plan is complete enough for owner review. It **never** means the proposal is eligible or sendable. `SUBMISSION_READY` is structurally unreachable in this v1 generation.

## Technical delivery spine

1. **Reference/runtime updates** — small reversible upgrades, reference-layer fixtures, migration/rollback evidence.
2. **Performance/security** — measure API/PostGIS/Sidekiq paths first; distinguish confirmed findings from hardening opportunities; bind fixes to regression and rollback evidence.
3. **Surface fixes** — failing-to-passing backend regressions plus explicit API compatibility notes; no claim of frontend ownership.
4. **Maintenance/bugs** — bi-weekly triage-to-merge loop with issue→commit→test→deploy-or-not-deployed receipts.
5. **Forward improvement list** — evidence-ranked backlog with impact, effort, dependency, decision owner, and rollback risk.

The public repository documents staging/production as self-contained EC2 hosts containing nginx, puma, Sidekiq, PostgreSQL/PostGIS and Redis. That is an **operational review target**, not a vulnerability claim.

## Usage

```bash
python -m revenue.wri_open_timber_portal.cli compile \
  revenue/wri_open_timber_portal/fixtures/public_known.json --format json

python -m revenue.wri_open_timber_portal.cli compile \
  revenue/wri_open_timber_portal/fixtures/public_known.json --format markdown

python -m revenue.wri_open_timber_portal.cli verify PACKET.json REPORT.json
```

The verifier replays the historical receipt and re-evaluates source freshness at process-owned current UTC time. Strict JSON rejects duplicate keys and non-finite values; CLI ingress requires a bounded regular file and refuses final-component symlinks where `O_NOFOLLOW` is available.

## Authority ceiling

No WRI contact, proposal submission, signature/certification, named-person commitment, contract acceptance, production deployment, award, payment, or revenue recognition is authorized or claimed here. Pricing remains owner-decision-required until the controlling procurement instructions are recovered.
