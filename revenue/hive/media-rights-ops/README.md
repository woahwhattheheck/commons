# Content Rights & Usage-Window Operations Desk

Local-first operations software for agencies, brand teams, and media operators that need an exact answer to an operational question: **does this planned placement fit the authority facts the owner has supplied, and what currently needs renewal or retraction review?**

The desk stores immutable asset fingerprints and derivative lineage, normalized grant facts, exact placement requests, grant revocations, and an audit ledger. It evaluates channel / territory / time-window scope, records permitted placements idempotently, blocks changed replays, and produces expiry/renewal and retraction-review queues plus deterministic JSON, CSV, Markdown, and receipt hashes.

## Truth and authority boundary

This is **not** a copyright, contract, licensing, fair-use, or ownership determination engine. `READY_ON_SUPPLIED_AUTHORITY` means only that a requested placement fits the owner-normalized facts currently stored in the desk. It never infers rights, parses legal language, creates a grant, contacts a creator/licensor, uploads/publishes/removes media, logs in to a platform, or moves money.

All production mutations are local SQLite writes. The optional HTTP desk binds to loopback only.

## Commercial hypothesis

`$25,000 fixed / PROPOSED_NOT_ACCEPTED`: one entity, one normalized grant schema, up to 5,000 assets/versions and 20,000 grant/placement rows, target 10 business days after complete normalized intake. Optional `$1,500/month` operations support is a hypothesis only after a delivered fixed-scope implementation. No buyer acceptance, contract, payment, cash, or revenue is claimed here.

## Quick start

```bash
cd revenue/hive/media-rights-ops
python rights_ops.py import desk.sqlite3 example_manifest.json --at 2026-09-15T06:00:00Z
cat > intent.json <<'JSON'
{"asset_id":"cut-a-15s","channel":"instagram","territory":"US","starts_at":"2026-10-01T12:00:00Z","ends_at":"2026-10-15T12:00:00Z"}
JSON
python rights_ops.py evaluate desk.sqlite3 intent.json
python rights_ops.py queues desk.sqlite3 --as-of 2026-12-10T00:00:00Z --horizon-days 30
python rights_ops.py export desk.sqlite3 bundle --as-of 2026-12-10T00:00:00Z
python rights_ops.py serve desk.sqlite3 --host 127.0.0.1 --port 8765
```

To record a placement, add a stable `request_id` to the intent and use `place --at ...`. The same request and content replay without duplication; the same request ID with changed content fails closed. `revoke <grant_id> --at ...` is immutable: a revocation can be replayed exactly but not silently rewritten. A recorded placement affected by revocation enters the retraction-review queue; the desk does not remove it from any provider.

## Acceptance surface

The hostile suite covers exact derivative lineage; allowed placement; wrong channel and territory; future/expired/revoked grants; unlicensed/unknown assets; request replay mutation; HOLD-without-write; immutable revocation; renewal/expiry queues; concurrent duplicate placement -> exactly one durable row; restart behavior; deterministic exports; create-exclusive publication; duplicate-key, floating-point, non-finite, cyclic/missing-lineage, duplicate authority rows, and naive-time failures.

Run both ordinary and optimized modes:

```bash
python -m unittest -v test_rights_ops.py
python -O -m unittest -v test_rights_ops.py
python -m py_compile rights_model.py rights_store.py rights_export.py rights_http.py rights_ops.py test_rights_ops.py
```

Input JSON is bounded to 8 MiB, UTF-8 only, duplicate-key rejecting, floating-point/non-finite rejecting, exact-schema validated, and timestamps must be offset-aware. Export directories are create-exclusive and files are mode `0600`.
