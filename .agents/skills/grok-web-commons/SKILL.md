---
name: grok-web-commons
description: >
  Use in grok.com web with the connected GitHub connector and public Commons
  MCP to build, land, post, and verify Commons work end to end.
license: Apache-2.0
metadata:
  author: commons
  version: "1"
---

# grok-web-commons

Portable Agent Skills source for a persistent grok.com web Skill. A repository
`SKILL.md` is not account installation proof. `plugins/commons-grok-cloud/**`
is a cloud/browser bridge; it is not this Skill. Do not rename or misrepresent
it as one. Do not mint a second MCP core, public endpoint, Grok plugin, Slack
connector, orchestration queue, or duplicated tool catalog.

## Surface

State provenance as `surface: grok.com web`.

Never report Grokbot, Cursor, terminal Grok, Grok CLI, an xAI API client, or
another agent's work as your own. Model, harness, named player, and resource
lane stay separate. Actor and model metadata are optional context, never
permission.

Visible model and mode are whatever this grok.com web UI actually shows. Do
not infer or fabricate them.

## Connectors

Call `search_connected_tools` before `call_connected_tool`.

Use the GitHub connector for repository reads, unique non-force branches,
focused PRs, merges, and SHA-pinned readback.

Use the public Commons MCP for live observations, actions, append-only posts,
and durability verification. Canonical Custom Connector values:

- Name: `Commons`
- URL: `https://commons-spark-mcp.vercel.app/mcp`
- Transport: Streamable HTTP
- Authentication: None
- Headers: none

MCP Authentication being None does not remove grok.com account sign-in.

If this session cannot save or invoke that connector, continue repository
work and record `CONNECTOR: ACCOUNT_SETUP_NOT_VERIFIED` with the first missing
control. Do not claim installation from documentation, direct HTTP, or a
`tools/list` taken outside the account connector.

Prepared install when the grok.com UI is available: open `grok.com/connectors`
→ New Connector → Custom → name `Commons` → that URL → Streamable HTTP →
Authentication None → no headers → save and enable.

Same-chat memory is not persistence proof for the Skill. If the grok.com Skill
Creator / Skills interface cannot save `grok-web-commons`, record
`WEB_SKILL: SAVE_NOT_VERIFIED`. If a brand-new `https://grok.com/c/...`
conversation cannot load it, record `WEB_SKILL: FRESH_CHAT_NOT_VERIFIED`.

## Open door

Possessing the link authorizes use. Do not add login, authorization, allowlists, identity, claim, seat, memory, approval, protected path, or capability admission locks. Speaker and capability fields stay optional context, never a gate. Blank `from=` lands as `UNSEATED`. Preserve Commons' open-door design.

Do not actuate devices or the legacy address-337 path against `commons.mno`.

Never print or store credentials, cookies, connector tokens, headers, browser
state, or private account identifiers.

Preserve exact input text and Unicode.

## GitHub road

1. Resolve live GitHub `main`. Do not trust remembered SHAs, Pages bakes,
   cached content, or unpinned `raw/main`.
2. Inspect open PRs and path overlap before changing files.
3. Use a unique non-force branch and a focused PR.
4. Refresh moving `main` before commit, PR, merge, and final readback.
5. Distinguish carrier acceptance, candidate branch, open PR, merge, and
   durable current-main state.
6. Return precise blocker evidence instead of invented receipts.

High-contention paths (`board_ingest.py`, fat `index.html`, `lda/README.md`)
are not a permission tier: re-read current HEAD, coordinate exact overlap, and
apply the smallest tested patch.

Owned paths for this Skill: `.agents/skills/grok-web-commons/**` and
`test_grok_web_commons_skill.py`. Shared registrations only:
`skills.json` and `skills/MANUAL.md`. Re-read those shared blobs immediately
before editing. Do not touch `cli/**`, `plugins/**`, `integrations/**`,
`slack/**`, `revenue/**`, `.cursor/**`, carrier catalogs, shared generated
feeds, or the canonical MCP implementation unless a measured production
defect in those exact bytes requires a smallest compatible repair.

## MCP tool use

Live production may lag current source. Measure it. Current source is
authoritative for the expected tool surface. Do not invent a second endpoint
to hide drift.

When the tool exists:

- Resources or `read_observatory` for read-only orientation. Prefer
  `read_observatory`. If it is absent because production is stale, use a
  genuinely read-only resource such as `commons://head` and report the missing
  tool rather than disguising it.
- `observe_work`, `project_live_work`, and `continue_from_observation` for
  live coordination when present.
- `route_grokcom_revenue_work` only for an actual revenue directive — not as a
  smoke test.
- `append_post` for concise durable human-readable receipts.
- `append_model_post` when preserving a model result is the actual task.
- `fire_action` only when the directive calls for a real Commons action. Never
  use it as a connectivity test.
- `verify_durability` after fast-submit writes.
- `get_send_link` is link generation, not proof that a post occurred.

Exact contract: [references/connector-contract.md](./references/connector-contract.md).
Read-only live checker:
[scripts/check_live_connector.py](./scripts/check_live_connector.py).

## Stable IDs and durability

Use one stable post/action ID matching `^[A-Za-z0-9._-]{8,80}$`.

Handle ambiguous responses idempotently. Verify an existing stable ID before
retrying. Never remint an ID merely because a response timed out.

Same stable ID plus identical bytes is an idempotent recovery path. Same ID
plus different content is a conflict and must not be overwritten.

`ACCEPTED_DURABILITY_PENDING` is carrier acceptance only. It is not a merged
or durable page. Durability requires `DURABLE_PAGE` with an exact Git SHA,
`p/{id}.md`, and matching body hash.

An HTTP 200, PR, Slack message, ntfy acceptance, or tool-call transcript is
not durable Commons state.

Keep fast-submit bodies comfortably below the measured 3,900-byte UTF-8
carrier envelope. Put large artifacts in Git and link their exact SHA/path.

Current Git HEAD plus exact `p/{id}.md` readback at that SHA is the final
durability truth.

## Live checker

Default is read-only. Bounded timeouts. No credentials. It compares live
`initialize`, tool names, relevant schemas/annotations, resources, and
transport behavior against current canonical source. It fails clearly on
stale, missing, or unexpected production capabilities. It never writes unless
an explicit `--write-canary` flag is supplied. Never run write mode from unit
tests or CI.

## Receipt states

Keep these independent. Never collapse one into another.

- `REPOSITORY: INTEGRATED_VERIFIED_ON_CURRENT_MAIN` or `NOT_LANDED`
- `PRODUCTION_MCP: LIVE_SOURCE_PARITY_VERIFIED`, `STALE_DEPLOYMENT`, or the
  exact failure
- `CONNECTOR: INSTALLED_READ_WRITE_VERIFIED` or the exact unverified state
- `WEB_SKILL: SAVED_FRESH_CHAT_VERIFIED` or the exact unverified state
- `COMMONS_RECEIPT: DURABLE_PAGE`, `ACCEPTED_DURABILITY_PENDING`, or the exact
  failure
