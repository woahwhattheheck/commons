# Localized Media Release & Variant Operations Desk

A local-first operations desk for teams that already possess source media and owner-supplied release authority, but need a deterministic way to manage localized variants, exact revision approvals, stale-parent invalidation, and a reproducible handoff package.

**Commercial hypothesis:** `$20,000 fixed` for one owner / up to 250 source titles and 2,500 locale/territory variants; optional `$1,000/month` support after delivery. These are **PROPOSED_NOT_ACCEPTED** terms, not revenue or buyer acceptance.

## What the product does

- binds every localized artifact to an exact SHA-256 source generation;
- records owner-declared required `(locale, territory, kind)` variants;
- records reviewer approval only against the exact current revision + content hash;
- invalidates release readiness automatically when source or localized bytes change;
- rejects replay/remint conflicts through durable request-id idempotency;
- serializes writes with SQLite `BEGIN IMMEDIATE` and survives reopen/retry;
- produces a deterministic ZIP containing `release.json`, `release.md`, and `receipt.json`;
- recomputes the package from current retained state for exact verification;
- creates exports with an exclusive, no-follow leaf under a retained parent-directory descriptor, refusing overwrite/symlink targets and removing only its own created inode on failure.

## Authority ceiling

This is working operations software, not a legal/rights/translation-quality diagnostic. It **does not** infer or interpret contracts, licenses, fair use, cultural suitability, or translation quality. `rights_ready` is an owner-supplied fact. `external_publish_authorized` is always `false` in the generated packet. The desk does not contact licensors/translators/customers, publish to platforms, mutate payment/accounting/provider systems, deploy externally, or spend money.

## Quick demo

All bundled demo media/text is fictional and self-authored.

```bash
cd revenue/hive/localized-media-release-desk
python -B demo.py --workdir /tmp/localized-release-demo
python -B desk.py --db /tmp/localized-release-demo/localized-release.sqlite3 status --title-id demo-title
python -B desk.py --db /tmp/localized-release-demo/localized-release.sqlite3 verify --title-id demo-title --package /tmp/localized-release-demo/localized-release-demo.zip
```

A successful demo finishes at `READY_FOR_LOCAL_HANDOFF`; it does **not** authorize external publication.

## CLI workflow

Create a title from exact local source bytes and a strict JSON requirement list:

```bash
python desk.py --db desk.sqlite3 create-title \
  --request-id create-001 \
  --title-id campaign-master \
  --source ./master.mov \
  --required ./required.json
```

Record the owner-supplied rights-readiness fact:

```bash
python desk.py --db desk.sqlite3 set-rights-ready \
  --request-id rights-001 --title-id campaign-master --ready true
```

Add a required localized artifact. The result returns the exact revision and SHA-256 needed for approval:

```bash
python desk.py --db desk.sqlite3 add-variant \
  --request-id es-001 --title-id campaign-master \
  --locale es --territory US --kind subtitle --artifact ./es-US.srt
```

Approve only the exact current revision/hash:

```bash
python desk.py --db desk.sqlite3 approve \
  --request-id es-approve-001 --title-id campaign-master \
  --locale es --territory US --kind subtitle \
  --reviewer reviewer-es --revision 1 --sha256 <returned_sha256>
```

Inspect holds:

```bash
python desk.py --db desk.sqlite3 status --title-id campaign-master
```

Export only when every owner-declared variant is current + approved and `rights_ready=true`:

```bash
python desk.py --db desk.sqlite3 export \
  --title-id campaign-master --out ./campaign-master-release.zip
```

The export is create-exclusive: an existing file or symlink at that leaf is never replaced.

## Fail-closed semantics

Ordinary current operations own process UTC; there is no `--as-of` or caller clock override. A source mutation leaves existing variants bound to the old source generation, producing `STALE_SOURCE_BINDING` until each required variant is explicitly revised. A variant mutation increments its revision and immediately makes prior approvals stale. An approval must match the current title, variant key, revision, content SHA-256, and source generation. Request IDs are durable: exact retries return the first result; the same request ID with different semantics is rejected.

## Tests

```bash
python -B -m unittest -v test_desk.py
python -O -B -m unittest -v test_desk.py
python -m py_compile desk.py demo.py test_desk.py
```

The hostile suite covers duplicate JSON keys, duplicate required variants, missing readiness, stale variant approval, source-generation invalidation, idempotency conflict/remint, cross-title approval reuse, undeclared variants, deterministic reopen/package bytes, create-exclusive export, symlink preservation, package tamper detection, and SQLite boolean constraints.
