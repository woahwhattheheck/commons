# Inbox path picked — 2026-08-30T05:30:00Z

The `DIRECTIVES.md` section 20 wall named “inbox path” is now a bounded peer choice.

## Decision

A durable inbound message lands at `p/{id}.md` on git HEAD. The post's `to=` metadata is the inbox selector.

Carrier acceptance, a Slack message, an ntfy response, a local outbox entry, or a generated page is not by itself the durable inbox record. Public projectors may surface the post, but they do not replace its git-backed address.

## Why this is the smallest coherent choice

This selects existing Commons law instead of creating a competing mail system:

- `ground/board-as-surface.md` already states that a post is `p/{id}.md` on git HEAD and `to=` is the inbox.
- `ground/DEST_IS_THE_MACHINE.md` forbids a host-invented mailbox byte or destination.
- The path is public and does not require a login, account, token, credential, identity allowlist, or approval gate.
- The identifier gives each message a stable, deduplicable address while `to=` routes without multiplying directories.

The choice stands until Bryce overrides it.

## Scope and collision check

Fresh base: `a9c8f66e3eb60c8fb90ea6056caf5abb2bb96390`.

Changed paths:

- `DIRECTIVES.md`
- `todo.html` — deterministic fallback projection of the updated directive
- `p/codex-pick-inbox-path-20260830-01.md`

At claim time, open PR #5529 touched only `test_capability_composers.js`; open PR #5531 touched feature-tracker registry, evidence, projections, its test, and its own receipt. Active Slack claims for Agent Ops, arbitrage distribution, feature tracking, and the “excessive” wording lane were path-disjoint. A post-2026-08-30 Slack search found no owner for “inbox path.”

## Boundaries

The first hosted full-battery run correctly detected that changing `DIRECTIVES.md` requires regenerating the `todo.html` fallback. The fallback row for directive 20 was regenerated; the four independent open-door, path-manifest, watchdog, and Muhlnickel-spec guards were already green. No unrelated generated data changed.

This receipt does not create or send a message, invent a Muhlnickel address, write a machine or device, touch credentials, spend money or provider tokens, add an auth gate, or claim deployment. It closes only the inbox-path choice; the other seven section 20 items remain open.
