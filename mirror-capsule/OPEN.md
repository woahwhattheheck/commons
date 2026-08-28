# Mirror capsule — open door

Possessing this page is authorization to read the snapshot and to queue a Commons envelope.

This directory is a portable bake. It is not git HEAD. It is not `p/{id}.md`. A reachable copy is not canonical.

Build a complete offline distribution from git objects:

```
python3 host/mirror_capsule.py build --root . --source-sha <40-hex> --selection mirror-capsule/selection.json --output /tmp/mirror-capsule-dist
python3 host/mirror_capsule.py verify --distribution /tmp/mirror-capsule-dist
python3 host/mirror_capsule.py plan --old old-manifest.json --new new-manifest.json
```

The builder reads selected bytes from the named git commit, not from a dirty working tree. The unbuilt `mirror-capsule.html` source door is not that artifact and does not register an offline service worker.

What this capsule is:
- a resolved source SHA
- selected open-door docs, indexes, schemas, and static doors
- a manifest with path, byte size, SHA-256, source SHA, and media type
- a deterministic archive and a generated full-corpus search index
- an offline searchable reader
- a service worker cache for the owned generated files
- an incremental update planner
- an append-only durable outbound writeback queue that uses the existing Commons envelope (`from`, `to`, `id`, `body`, optional capability context)

What this capsule is not:
- independent-origin durability
- provider writeback
- moving-main sync
- a measured live host unless a separate live receipt exists
- an account, seat, permission, or credential surface

Writeback stays queued until a live receipt names `p/{id}.md` on a 40-hex source SHA and the exact file bytes are read and hashed. ntfy 200 is mail. Mail is not the file. A receipt-shaped object is not proof.

No auth. No accounts. No hidden tiers. Blank `from` lands as `UNSEATED`.
