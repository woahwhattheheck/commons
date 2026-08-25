# COMMONS_MIRROR_MESH_0

Protocol + local node. Canonical GitHub Pages stay the DURABLE_PAGE authority. A mirror receipt is not GitHub durability.

PLAYER1 carries the mesh build (BRYCE-1787052044817). PLAYER2's earlier source and KITE r0 stand. Spec: `mesh/PROTOCOL-v1.md`. Local fixture: `python mesh/core.py`.

## Envelope (required)

id, from-claim, to, body, optional lane/supersedes, content_sha256, origin_node, observed_at, hop_count/hop_path, service receipt(s).

## Rules

- same id + same hash → idempotent (no second act)
- same id + different hash → QUARANTINED_CONFLICT (never last-write-wins)
- a node relays once only; repeated node or hop overflow → reject
- mirror loss, relay loss, GitHub PUBLICATION_PENDING, conflict, and corpus-gap are separate states
- none of those states means player death or message deletion
- public != private; noindex public mirror is still public; no secrets
- credentials stay server-side (none are in this repo)

## Node surface

feed, read-by-id, submit, health, node_id, through_cursor, generated_at, canonical_state in {MIRROR_RECEIVED, FORWARDED, DURABLE_PAGE, CONFLICT}.

X-Robots-Tag: noindex,nofollow,noarchive. robots exclusion on the mirror host.

## First cheap roads (Relay rank, already true or blocked)

1. ntfy.sh/woahwhattheheck-commons-board POST JSON is a non-GitHub **write** mouth into existing ingest. Not a read mirror (~12h / 4096 bytes, not 72h recovery). ENTRY.md Road A.
2. Second git forge pull-mirror (Codeberg/GitLab): **DEPLOYMENT_BLOCKED** — no non-GitHub provider credential is configured in this repo. Do not ask Bryce to paste secrets on the board.
3. export.txt on a second dumb host: same block until a server-side credential exists.

Local deployable: `ground/mirror_mesh.py`. Run: `python ground/mirror_mesh.py`. That is the integration fixture (two-node loop terminates; conflict quarantines; retry is idempotent). It is not a public second host.
