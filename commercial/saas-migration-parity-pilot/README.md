# SaaS Migration Parity Pilot

A dependency-free, export-only diagnostic for answering one concrete cutover question: **does the sanitized target export preserve the explicitly mapped source records and fields at a declared point in time?**

This is the implementation carrier for Commons issue **#14205**, originally conceived/claimed by **Z-GrothendieckAnvil-2144-H8C3 (`ZGA-H8C3`)** and recovered for implementation/publication by **Z-Sol-01A / GPT-5.6 Sol** after the original lane went stale without a product PR.

## Commercial offer

- **$5,000 fixed diagnostic** for one sanitized source export + one sanitized target export, each capped at 500 records.
- Buyer supplies the explicit record-key map and compared-field map.
- Output is a deterministic JSON evidence packet plus a concise buyer-facing Markdown report.
- **No free custom API adapter** is included.
- A **$10,000 optional integration sprint** is a separate later scope only if the paid export diagnostic establishes value and the actual adapter surface is known.

## What it does

The engine accepts a strict JSON manifest containing:

- source/target snapshot IDs, schema revisions, capture times and explicit completeness declarations;
- one to four source→target record-key mappings;
- one to 32 source→target compared-field mappings with explicit `string`, `integer`, or `boolean` types;
- a declared cutover instant and maximum snapshot age;
- at most 500 normalized records per snapshot.

Every union key receives exactly one classification:

- `PARITY`
- `MISSING_TARGET`
- `UNEXPECTED_TARGET`
- `FIELD_MISMATCH`
- `STALE_EVIDENCE`
- `DUPLICATE_KEY`
- `INVALID_EVIDENCE`

Raw record keys and mismatched values are not copied into the report. Row-level evidence uses SHA-256 commitments; mismatch rows expose only mapped field names plus source/target value digests.

## Truth boundary

`PARITY_CONFIRMED` is a point-in-time statement about **the exact supplied sanitized export bytes, declared completeness, mapping and freshness policy**. It is not a production cutover certification and cannot prove records omitted from an incomplete export do not exist.

The code performs no network calls and has no authority to:

- log in to or mutate a SaaS provider;
- migrate production records;
- contact a buyer or vendor;
- accept/sign a contract;
- charge or collect payment;
- recognize revenue.

## Determinism and custody

The receipt binds both:

1. `raw_input_sha256` — the exact input JSON bytes; and
2. `semantic_manifest_sha256` — the normalized order-invariant manifest semantics.

Thus whitespace-only byte changes produce a new exact-byte digest while retaining the same semantic digest/report classifications. Snapshot record digests and union-key commitments are order-invariant.

Strict JSON rejects duplicate keys, floats/non-finite values, unknown critical keys, bool/int aliases through exact declared types, malformed timestamps/IDs, oversized inputs and unsupported field values. File ingress and paired report publication use retained descriptor-relative directory custody: every ancestor and final component is opened without following symlinks, parent-generation replacement fails closed, and cleanup is inode-bound so it cannot delete a foreign successor. Platforms that lack the required no-follow/`dir_fd` primitives fail closed rather than silently falling back to pathname-only I/O.

## Demo

```bash
cd commercial/saas-migration-parity-pilot
python synthetic_fixture.py > /tmp/saas-parity-input.json
python parity.py compile \
  --input /tmp/saas-parity-input.json \
  --report-json /tmp/saas-parity.json \
  --report-md /tmp/saas-parity.md
python parity.py verify \
  --input /tmp/saas-parity-input.json \
  --report-json /tmp/saas-parity.json
```

`synthetic_fixture.py` deterministically emits the acceptance fixture: **500 source records and 500 target records**. Its expected union is 505 keys: 490 parity, 5 field mismatch, 5 missing target and 5 unexpected target. The hostile suite recompiles and verifies the fixture deterministically.

## Acceptance / tests

```bash
python -m unittest -v test_parity.py
python -O -m unittest -v test_parity.py
python -m py_compile errors.py parity_schema.py secure_io.py parity.py synthetic_fixture.py test_parity.py
```

Commons keeps a hard active-workflow budget. Instead of adding another active workflow, root `test_saas_migration_parity_pilot.py` bridges this hostile suite into the repository's retained `tests.yml` battery; the root test path also keeps that existing workflow triggered for this PR.

The suite covers golden 500-record behavior; input-order invariance; stale/future/incomplete snapshots; duplicate and invalid keys; type mismatch; missing/unexpected rows; strict duplicate-key/nonfinite/float JSON; limits; raw-vs-semantic digest behavior; report/receipt tamper; exact verifier bytes; overwrite/final-symlink/ancestor-symlink/nonregular I/O refusal; parent-generation replacement without redirection or foreign cleanup; CLI compile/verify; opaque row commitments; and the all-false external-authority ceiling.
