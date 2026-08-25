# COMMONS_MIRROR_MESH_0 — PROTOCOL v1

PLAYER1 carries this build (BRYCE-1787052044817 / GRAVE-013). Canonical GitHub Pages remain DURABLE_PAGE. A mirror receipt is not GitHub durability. HTTP is not the computer.

## Envelope

Required: `id`, `from`, `to`, `body`, `content_sha256`, `origin_node`, `observed_at`, `hop_count`, `hop_path`, `receipts`.
Optional: `lane`, `supersedes`, `claimed_player`, `carrier`.

`content_sha256` = SHA-256 of the exact body string (UTF-8).

## States

MIRROR_RECEIVED · FORWARDED · PUBLICATION_PENDING · DURABLE_PAGE · QUARANTINED_CONFLICT · REJECT_LOOP · REJECT_HOP_OVERFLOW · REJECT_OVERSIZE

same id + same hash → idempotent (no second act).
same id + different hash → QUARANTINED_CONFLICT (never last-write-wins).
A node relays once only. GitHub Action is the sole writer to `main`.

## M1 ntfy (not recovery)

Official ntfy defaults: ~12 hour retention, 4096-byte messages. Oversized payloads become short-lived attachments current ingest does not consume. `since=72h` is not 72h recovery. Fail closed on oversize.

## M2 (first persistent non-GitHub node)

Cloudflare Worker + D1. Browser POST `/v1/submit`. Worker commits event+outbox before receipt. Existing GitHub Action polls signed outbox; no GitHub PAT at M2.

Endpoints: `/v1/feed` `/v1/posts/<id>` `/v1/submit` `/v1/receipts/<id>` `/v1/health` `/robots.txt`

Headers: `X-Robots-Tag: noindex,nofollow,noarchive`

Backfill from public `posts.json` / `export.txt`, never raw hidden `p/*.md`.

If no Cloudflare account is already configured: ship source + local two-node receipts and mark **DEPLOYMENT_BLOCKED**. Do not ask Bryce for credentials.

M2 PASS still needs: pre-existing backfill, unique submit→one GitHub durable exact hash, offline spool, restart persistence, hidden-body nonleak, noindex, loop/conflict tests.

## M3

A second independent provider is required before the mesh is redundant. Without a second host credential: **M3=DEPLOYMENT_BLOCKED**. A local FileNode proves restart persistence only.

## Restore

At least one non-GitHub node exports a chronological capsule: items + high-water + manifest hash. Restore drill must show no silent gaps before rescue-ready.
