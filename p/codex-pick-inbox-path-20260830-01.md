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

Fresh successor base: `68e8a433e92477ad4c0cff9b94c7003fc62a3436`.

Changed paths:

- `DIRECTIVES.md`
- generated `todo.html`
- `p/codex-pick-inbox-path-20260830-01.md`

PR #5584 preserved the decision but omitted the generated TODO fallback, so the repository battery failed `test_battery_red.py::test_live_tree_has_the_leftover`. This successor regenerates that projection from the same directive instead of weakening the test.

At successor claim time, open PR #5598 touched only `test_capability_composers.js`; open PR #5531 touched feature-tracker registry, evidence, projections, its test, and its own receipt. Active claims for arbitrage distribution, Grok queue recovery, and machine/device proof were path-disjoint.

## Boundaries

This receipt does not create or send a message, invent a Muhlnickel address, write a machine or device, touch credentials, spend money or provider tokens, add an auth gate, claim deployment, or alter unrelated generated indexes. It closes only the inbox-path choice; the other seven section 20 items remain open.
