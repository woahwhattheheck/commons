# Content Rights & Usage-Window Operations Desk

Local-first operations software for agencies, brand teams, and media operators that need an exact answer to an operational question: **does this planned placement fit the authority facts the owner has supplied, and what currently needs renewal or retraction review?**

The desk stores immutable asset fingerprints and derivative lineage, normalized grant facts, exact placement requests, grant revocations, and an audit ledger. It evaluates channel / territory / time-window scope, records permitted placements idempotently, blocks changed replays, and produces expiry/renewal and retraction-review queues plus deterministic JSON, CSV, Markdown, and receipt hashes.

## Truth and authority boundary

This is **not** a copyright, contract, licensing, fair-use, or ownership determination engine. `READY_ON_SUPPLIED_AUTHORITY` means only that a requested placement fits the owner-normalized facts currently stored in the desk. It never infers rights, parses legal language, creates a grant, contacts a creator/licensor, uploads/publishes/removes media, logs in to a platform, or moves money.

Derivative lineage is provenance only, not authority inheritance. A grant authorizes only its exact `asset_id`; a grant on a parent/master does **not** authorize a child/derivative unless the owner supplies a separate grant fact for that exact child asset.

All production mutations are local SQLite writes through the CLI. The optional HTTP desk binds to loopback and is read-only with respect to state: it exposes snapshot/evaluation/queue reads, while HTTP `/api/place` and `/api/revoke` fail closed with `405`. Use CLI `place` / `revoke` for mutations.

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

To record a placement, add a stable `request_id` to the intent and use CLI `place --at ...`. The same request and content replay without duplication; the same request ID with changed content fails closed. CLI `revoke <grant_id> --at ...` is immutable: a revocation can be replayed exactly but not silently rewritten. A recorded placement affected by revocation enters the retraction-review queue; the desk does not remove it from any provider.

Export publication is create-exclusive and retains the existing output-parent generation, the newly created output directory, and every created leaf by filesystem identity. The output parent must already exist as a real directory; the exporter will not recursively create or follow a symlinked parent. Parent observation/open, child creation, leaf creation, rollback, and final success are identity-fenced. Writes are descriptor-relative with no-follow/exclusive creation; a parent replacement, pathname swap, renamed directory, symlink successor, or replaced leaf fails closed rather than redirecting an `EXPORTED` result. Rollback identity-checks each transaction-created leaf and removes only the transaction-created child through the retained parent descriptor, so foreign successors are never deleted by name. Secure publication therefore requires a platform with descriptor-relative `open`/`mkdir`/`stat`/`unlink`/`rmdir`, `O_DIRECTORY`, and `O_NOFOLLOW`; unsupported platforms fail closed instead of silently using a weaker export path.

## Acceptance surface

The hostile suite covers exact-asset authority; parent-grant/child-derivative non-inheritance; HTTP mutation fail-closure with unchanged durable state; allowed placement; wrong channel and territory; future/expired/revoked grants; unlicensed/unknown assets; request replay mutation; HOLD-without-write; immutable revocation; renewal/expiry queues; concurrent duplicate placement -> exactly one durable row; restart behavior; deterministic exports; create-exclusive publication; output-parent generation replacement; export-directory pathname replacement/redirection; failure rollback preserving a foreign successor; duplicate-key, floating-point, non-finite, cyclic/missing-lineage, duplicate authority rows, and naive-time failures.

Run both ordinary and optimized modes:

```bash
python -m unittest -v test_rights_ops.py
python -O -m unittest -v test_rights_ops.py
python -m py_compile rights_model.py rights_store.py rights_export.py rights_http.py rights_ops.py test_rights_ops.py
```

Input JSON is bounded to 8 MiB, UTF-8 only, duplicate-key rejecting, floating-point/non-finite rejecting, exact-schema validated, and timestamps must be offset-aware. Export directories are mode `0700`; export files are mode `0600` subject to the process umask.
