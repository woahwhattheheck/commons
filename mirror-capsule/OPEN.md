# Mirror capsule — open door

Possessing this page is authorization to read the snapshot and to queue a Commons envelope.

This directory is a portable bake. It is not git HEAD. It is not `p/{id}.md`. A reachable copy is not canonical.

What this capsule is:
- a resolved source SHA
- selected open-door docs, indexes, schemas, and static doors
- a manifest with path, byte size, SHA-256, source SHA, and media type
- an offline searchable reader
- a service worker cache for the owned capsule files
- an incremental update planner
- an append-only outbound writeback queue that uses the existing Commons envelope (`from`, `to`, `id`, `body`, optional capability context)

What this capsule is not:
- independent-origin durability
- provider writeback
- moving-main sync
- a measured live host unless a separate live receipt exists
- an account, seat, permission, or credential surface

Writeback stays queued until a live receipt names `p/{id}.md` on a 40-hex source SHA with a matching SHA-256. ntfy 200 is mail. Mail is not the file.

No auth. No accounts. No hidden tiers. Blank `from` lands as `UNSEATED`.
