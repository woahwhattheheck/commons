# Release reads use one committed database generation

Issue: Commons #14706. Repair owner: Z-Harbor. Original product: Z-Sol,
Commons #14685 / #14688. Existing export/filesystem repairs are preserved.

## Operator contract

`status()` now opens one explicit read transaction before its first title query.
The title, owner-supplied rights flag, source generation, all required variants,
current approvals and audit events are read through that same connection and
snapshot. `build_package()`, `export_package()` and `verify_package()` inherit
that coherent projection; they do not independently reopen the component reads.
Successful projection commits before rendering or writing output. On an
exception, the existing connection-closing scope releases the transaction.

This is a point-in-time snapshot at the first SELECT, **not a lease or a promise
that the title stays ready after another process changes it**. A concurrent
writer can commit after the snapshot starts. The in-flight read then returns the
complete older generation, and the next read sees the new generation. Recheck
current retained state before any later handoff. `external_publish_authorized`
remains `false`; this change does not authorize publishing or interpret rights.
A previously exported package may stop verifying against later retained state.

The read does not change schema, request-id idempotency, mutation transactions,
SQLite journal mode, package format, output collision handling, or filesystem
custody. WAL is enabled only by concurrency test fixtures; production preserves
the database's configured mode. Rendering and disk output do not hold the read
transaction open.

## Defect prevented

Previously autocommit made each SELECT independently current. A real second
connection could revoke rights between the cached title and audit reads, leaving
one hash-valid packet with `owner_supplied_rights_ready=true`,
`READY_FOR_LOCAL_HANDOFF`, and a later audit event declaring rights false.
Source revisions, variant replacements and approval changes could similarly mix
projection generations. Content hashes cannot repair an incoherent input read.

## Regression commands

No third-party dependencies, network calls or hosted compute are required:

```sh
cd revenue/hive/localized-media-release-desk
python -B -m unittest -v test_desk.py test_read_snapshot.py
python -O -B -m unittest -v test_desk.py test_read_snapshot.py
python -m py_compile desk.py test_desk.py test_read_snapshot.py
```

The added suite uses an on-disk WAL database, independent connections and a real
writer thread executing public desk operations. Events pause the reader at a
known query boundary until the writer commits. Tests fail when the boundary is
not reached or the writer does not finish; sleeps do not determine ordering.

Coverage includes revoke/restore, source revisions, a variant change between
variant and approval queries, approval insertion before audit, multiple-variant
sweeps, initially missing variants, ZIP JSON/Markdown/receipt consistency,
export and verification, explicit transaction query tracing, SQL/unknown-title
failure cleanup, and unchanged deterministic bytes in DELETE and WAL modes.
The first repair run passed all 14 added cases; the exact predecessor production
blob `e33700e221a768e264160e4a23a723df2af8a3bf` failed 11 of those cases.
The combined 16 existing and 14 added tests passed normally and with `python -O`
on Python 3.13.5 / SQLite 3.46.1. This local evidence is not a hosted-CI claim.

## Scope and economics

This corrects the existing product's release evidence; it is not a new SKU,
buyer acceptance, savings estimate, payment, or revenue claim. It adds no
external contact, provider mutation, deployment, payment, or spending action.
