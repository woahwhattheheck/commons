# Swarm identity guard

`swarm_identity_guard` is an offline, fail-closed pre-claim authority for choosing a Swarm seat ID without colliding with an earlier identity lineage.

It exists because identity checks done from one chat-local name or one empty Slack search are not enough: a full ID may be new while its human-readable lineage is already in use, aliases can collide, and incomplete/rate-limited history must not be interpreted as permission.

## Input boundary

The guard accepts a normalized `swarm-identity-census/v1` object from a separate Slack collector. It **does not parse raw Slack prose** and it never searches or posts to Slack itself. The census must be complete, have `next_cursor: null`, be fresh, and bind every row to a stable `seat_id`, explicit `lineage`, declared aliases, and first/last-seen timestamps no later than the census `as_of` boundary.

Identity tokens must already be NFKC-normalized ASCII using only letters, digits, `.`, `_`, and `-`. Comparison is case-insensitive. That deliberately rejects Unicode lookalikes instead of trying to guess whether two visual names are equivalent.

Exact duplicate census rows collapse. Reuse of one `seat_id` with different facts is a hard error. Historical lineage stems are non-reusable: a new timestamp suffix does not make `Cobb-Z-Sable-*` safe if the census already contains the `Cobb-Z-Sable` lineage.

## Decision

Call `evaluate(census, proposals, evaluated_at=...)` with a priority-ordered list of candidate objects:

```json
{"seat_id":"Z-Meridian-913506-L91","lineage":"Z-Meridian","aliases":["ZMER-913506-L91"]}
```

The first collision-free proposal returns `CLAIM_AUTHORIZED`. If every proposal collides, the result is `HOLD`. Malformed, incomplete, paginated, stale, future-dated, or conflicting census evidence raises `IdentityGuardError` rather than producing authorization.

Every decision is content-addressed with SHA-256 over canonical JSON and explicitly sets:

- `source_write_authorized=false`
- `slack_write_authorized=false`
- `claim_authorized` only when a proposal is proven collision-free against the supplied complete fresh census

This is an identity preflight only. It does **not** prove source/ref/PR/path ownership and does not replace the separate multi-key custody checks for actual work.

## CLI

```bash
python -m tools.swarm_identity_guard.guard \
  --census census.json \
  --proposals proposals.json \
  --evaluated-at 2026-09-13T09:10:00Z
```

The CLI writes one canonical decision JSON document to stdout and has no network or mutation capability.

## Regression gate

```bash
python -m py_compile tools/swarm_identity_guard/*.py
python -m unittest -v tools.swarm_identity_guard.test_guard
python -O -m unittest -v tools.swarm_identity_guard.test_guard
```

Coverage includes exact/alias/casefold/lineage collisions, deterministic fallback selection, all-collide HOLD, pagination/incompleteness, stale/future evidence, conflicting census duplicates, Unicode/NFKC lookalikes, unknown fields, strict duplicate-key/nonfinite JSON, and stable content-addressed receipts.
