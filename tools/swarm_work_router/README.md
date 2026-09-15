# Swarm work router

`tools.swarm_work_router` turns one strict work-item record into a deterministic specialist-channel routing receipt. It exists to reduce two observed fleet failure modes: central-queue dogpiles and publication collisions across different transports.

## Authority ceiling

The router **does not send, post, submit, merge, pay, schedule, or otherwise mutate an external provider**. Every route receipt has `external_publish_authorized=false` and `side_effects_authorized=false`.

When `external_publish=true`, the receipt requires live Muse arbitration in DM `D0C1U7TUZEC` plus a current collision search before a separately authorized sender may mutate a provider. Email, contact form, DM, public post, GitHub external publication, and provider-submission transports do not create separate commercial identities: `publication_key` hashes normalized target + opportunity + purpose and deliberately excludes transport, worker identity, and message wording.

## Routing rules

Specialist channels are primary. `#delegations` and `#awaiting-merge` are **not** catch-all primaries; `#awaiting-merge` is primary only for `kind=merge_review`. Unknown kinds fail closed to `#coordination-channel-created-today-please-use` with `classification=HOLD_CLASSIFICATION_UNKNOWN`.

The current machine registry includes build demand, products/business packs, Hive build families, sales/leads/hot leads, GitHub inbox, feature/integration/bug/math/data-science bounty feeds, international competitions, shipped builds, coordination, todo scratch, and the two central queues.

## Work item

All keys are required and unknown keys fail closed:

```json
{
  "schema": "swarm-work-item/v1",
  "work_id": "ZFATHOM:invoice-desk-001",
  "kind": "product",
  "target": "Acme Incorporated",
  "opportunity": "Invoice reconciliation desk",
  "purpose": "Deliver fixed-scope operations software",
  "value_usd": 15000,
  "external_publish": false,
  "route_family": "none",
  "repository": "woahwhattheheck/smb-showcase-inventory",
  "artifact_scope": "apps/example/**"
}
```

For a prospective publication, set `external_publish=true` and choose one of `email`, `contact_form`, `direct_message`, `github_external`, `provider_submission`, or `public_post`. Internal work must use `route_family=none`.

## CLI

```bash
python -m tools.swarm_work_router.router route work.json
python -m tools.swarm_work_router.router channels
python -m tools.swarm_work_router.router scratch-open work.json > scratch-open.json
python -m tools.swarm_work_router.router scratch-clear work.json scratch-open.json > scratch-clear.json
```

The scratch compiler models the owner-directed `#todo` lifecycle. `CLEAR` requires the exact valid preceding `OPEN` receipt for the same work identity; reopening requires a valid preceding `CLEARED` receipt. The tool emits evidence only; the Slack message itself must still be created/deleted through Slack.

## Verification

```bash
python -m unittest -v tools.swarm_work_router.test_router
python -O -m unittest -v tools.swarm_work_router.test_router
```

Receipts are canonical JSON and carry a SHA-256 over every field except `receipt_sha256`. `verify_receipt()` recomputes the digest and enforces the no-side-effects ceiling.
