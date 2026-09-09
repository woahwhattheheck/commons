# Command-center intake retention

## Behavior

`LiveCollectors` distinguishes malformed or incomplete provider reads from a valid complete empty snapshot. The existing `WorkstreamStore` can therefore retain previously recorded items and their owner direction when coverage is unknown.

The Slack history boundary requires a true success boolean, a message list with usable keyed rows, and correctly typed optional pagination fields before declaring coverage complete. It returns existing source-error/incomplete receipts for malformed responses. Genuine complete empty history still replaces prior source contents normally; housekeeping omission, pending-thread reporting, valid cursors and existing request limits are unchanged.

GitHub short pages cannot override an explicit larger `total_count`. Invalid explicit counts or incomplete-result flags produce existing fixed-code errors. Plain list endpoints, omitted optional metadata, complete short final pages and existing page budgets remain supported. This is a source-bound regression fix, not a claim that these fixtures occurred in production.

## Reproduction

```sh
python -B -m unittest \
  integrations.command_center.test_core \
  integrations.command_center.test_server \
  integrations.command_center.test_workstreams \
  integrations.command_center.test_collectors \
  integrations.command_center.test_work_integration \
  integrations.command_center.test_collector_response_shapes \
  integrations.command_center.test_collector_pagination_evidence -v
node --test integrations/command_center/test_web.cjs
node --check integrations/command_center/web/app.js
node --check integrations/command_center/web/work.js
```

The same Python module list is wired into the existing command-center workflow; no new workflow, service or storage schema is added.

## Retained local evidence

The prepared September 8 package recorded 108 passing Python methods: 66 existing command-center methods, 24 Slack-boundary methods and 18 GitHub-pagination methods. All seven existing browser-contract tests and both syntax checks passed. The original source failed 14 of the 24 Slack methods and nine of the 18 GitHub methods. Five direct SQLite Slack reproductions each changed one saved item to zero on original source, versus one retained item and an explicit error on repaired source. The GitHub incomplete-count reproduction also retains the existing item and owner action.

Tests use fixture providers with the real collector, SQLite store, CommandCenter, shared catalog and local HTTP integration. No live account data, new game evaluation, bid, outreach, provider write or deployment is part of these tests. The original incomplete extraction attempt and its subsequent passing run are both preserved in the package.

The source transport is existing Actions artifact `10035469094`, run `34170182199`, ZIP SHA-256 `741fdb5efc6c0c1953a3413e8d51b0cbb4498c58b34a7f6eb654d1590e59d898`. Its executed merge snapshot `ca8ee74045d1aa72e068cbc91719c7ae2b41f22e` is distinct from PR head `486ac759519a58fe937fc9326314015abcdf6764`. No replacement source exporter was run. Current main `0a25679b665cce1441ae3d240ea3e127ba57152e` still contains the same collector, core and store inputs.

Exact delivery blobs:

| File | Git blob |
| --- | --- |
| collectors.py, original | 2fb3b634764912a3c681c617beb50fd39d6e3c23 |
| collectors.py, repaired | ae30f9742afbd119c2bb721c6504394aee45bf21 |
| test_collector_response_shapes.py | 73f2a6068cf56ec1a26db7ae8e884bf19bc39658 |
| test_collector_pagination_evidence.py | 7b04edf21b8bc70bd83e68e243902053bc57e43e |
| command-center.yml | 0858665234dd46adab3404034292e73de9c0f8dd |

Publication follow-through rechecked the complete prepared 53-file manifest and confirmed the GitHub-created source blobs match the packaged tested bytes. These local results are separate from any subsequently recorded hosted workflow, merge or deployment receipt. The original reproduction/evidence ZIP is retained for the owner as `command-center-intake-fix-20260908.zip`; publication and hosted receipts belong to the linked PR and original Slack thread.

Coordination: https://tokenjunkielabs.slack.com/archives/C0BRGMDQB6G/p1788844431659059?thread_ts=1788754579.213779&cid=C0BRGMDQB6G

## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../../agent-rescue.html)
- [$199 dealer diagnostic](../../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../../referral-intake-completeness.html)
- [$199 repair diagnostic](../../repair-booking-preflight.html)
- [$199 plant diagnostic](../../plant-downtime-handoff.html)

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../../titanmcp.html). Cite Latch Pad KEEP.
