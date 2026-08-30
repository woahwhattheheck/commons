---
name: feature-tracker
description: >-
  Evidence-derived shipped-state tracker. Use when adding a landed feature,
  projecting feature-tracker.html / feature-tracker.json, or deciding whether
  something is planned, source-built, tested, live, degraded, or superseded.
  Status is derived from git-visible registry and evidence. Chat, Slack, ntfy,
  open PRs, Pages, and claimed_status never promote LIVE.
license: Apache-2.0
metadata:
  author: commons
  version: "1"
---

# Feature tracker

Facts: [ground/FEATURE_TRACKER.md](../../../ground/FEATURE_TRACKER.md).
Door: [feature-tracker.html](../../../feature-tracker.html).
Machine: [feature-tracker.json](../../../feature-tracker.json).
Engine: [host/feature_tracker.py](../../../host/feature_tracker.py).
Registry: [features/registry/](../../../features/registry/).

`features.html` is the FEATURES board lane. Do not remint it.

## Do this

1. Mint `id` matching `^[A-Za-z0-9._-]{8,80}$`.
2. Write one new `features/registry/{id}.json`. Filename equals `{id}.json`.
3. Optionally write `features/evidence/{id}.json` (`SOURCE_PATHS`, `TEST_PATHS`, `GIT_SHA`, `BLOB`, `LIVE_MEASUREMENT`, `RECEIPT`, `SUPERSEDE`).
4. `python3 host/feature_tracker.py --write`
5. `python3 test_feature_tracker.py`
6. Unique branch from current main. Merge, not force. Read back on the official 40-character SHA. File `p/{id}.md`.

Same id + identical bytes is idempotent. Same id + different bytes is `CONFLICT`. Never overwrite. Add evidence or mint a new id.

## Do not

- Remint `features.html`
- Promote LIVE from chat, Slack, ntfy 200, an open PR, Pages, or `claimed_status`
- Collapse source-built into live
- Fabricate a `LIVE_MEASUREMENT` (needs a public URL and a 40-character SHA)
- Add auth, secrets, or a generated-history rewrite

LIVE is SOURCE_BUILT plus a valid `LIVE_MEASUREMENT` evidence row. HTTP is a bake. A cited blob that no longer matches the tree is stale; append a new evidence id. Do not overwrite.
