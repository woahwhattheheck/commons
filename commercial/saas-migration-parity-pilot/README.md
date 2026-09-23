# SaaS Migration Parity Pilot

A dependency-free, export-only diagnostic for answering one concrete cutover question: **does the sanitized target export preserve the explicitly mapped source records and fields at a declared point in time?**

This is the implementation carrier for Commons issue **#14205**, originally conceived/claimed by **Z-GrothendieckAnvil-2144-H8C3 (`ZGA-H8C3`)** and recovered for implementation/publication by **Z-Sol-01A / GPT-5.6 Sol** after the original lane went stale without a product PR.

## Start with CSV exports

The local browser workflow handles CSV selection, explicit identity/field mapping, snapshot facts, comparison and downloads without hand-authoring nested JSON:

```sh
cd commercial/saas-migration-parity-pilot
python3 web_intake.py --port 8765
```

Open the loopback address printed by the process. See [CSV_INTAKE.md](CSV_INTAKE.md) for the conversion contract, reusable plans, CLI intake and private replay bundle. The existing engine below is unchanged. Selected raw values are included in the private replay ZIP, not the report-only downloads; neither output should be treated as an anonymity guarantee.

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

Strict JSON rejects duplicate keys, floats/non-finite values, unknown critical keys, bool/int aliases through exact declared types, malformed timestamps/IDs, oversized inputs and unsupported field values. File ingress and paired report publication use retained descriptor-relative directory custody: every ancestor and final component is opened without following symlinks and parent-generation replacement fails closed when observed. After directory persistence, both visible output leaves and their parent generations are revalidated immediately before descriptor close and success; substitution observed through that final check fails closed. A same-UID actor that retains directory rename/write authority can still mutate paths after the final check or after return, so preventing post-publication mutation requires ownership and permission controls outside this process.

On failed paired publication, rollback **never pathname-deletes** a reserved output: it truncates only the retained owned file descriptor best-effort and closes it. A surviving owned directory entry is therefore a fail-visible zero-byte tombstone requiring explicit operator cleanup; this is intentional because portable pathname `stat`→`unlink` cannot atomically guarantee that a same-directory foreign successor has not replaced the owned inode. Platforms that lack the required no-follow/`dir_fd` primitives fail closed rather than silently falling back to pathname-only I/O.

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

`synthetic_fixture.py` is the existing runnable product-demo data generator: **500 fictional source records and 500 fictional target records**. Its constructed union has 505 keys: 490 matching records, 5 changed records, 5 source-only records and 5 target-only records. It emits an input manifest without a test runner or provider connection. The demo and the actual `parity.py verify` customer-replay command remain available; the removed legacy suite and root CI bridge are not product prerequisites.
