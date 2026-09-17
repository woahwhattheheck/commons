# Procurement submission assembly manifest

`revenue.procurement_solicitation_ingest.submission_assembly` turns retained **buyer-official submission-instruction generations** plus exact candidate artifact bytes into a deterministic, source-bound owner-review assembly state.

This closes the gap between “the response is written” and “the owner can see exactly what is still missing before submission.” It is deliberately **not** a portal automation or submission authority surface.

## Status contract

The compiler emits exactly one of four states:

- `ASSEMBLY_READY_FOR_OWNER_REVIEW` — every current required slot has one byte-verified candidate satisfying the retained constraints. Human review is still required.
- `HOLD_MISSING_REQUIRED_ARTIFACT` — at least one current required slot has no candidate artifact.
- `HOLD_SOURCE_CONFLICT` — source chronology/identity, slot identity, artifact custody/digest, buyer constraint, signature/certification evidence, or other retained truth is unsafe.
- `HOLD_DEADLINE_PASSED` — the exact active buyer-source deadline is at or before `evaluated_at` and no source/custody conflict exists.

A source conflict outranks the deadline state: the compiler will not use a deadline from a history it has already classified unsafe.

## What must be source-bound

Each buyer generation carries an exact source id/SHA-256, observed timestamp, monotonically increasing sequence, timezone-aware deadline, and a complete active slot snapshot. Each slot may retain only explicit facts from that source generation:

- required vs optional;
- order;
- exact base filename, when specified;
- admitted formats;
- maximum pages and/or bytes;
- signature / notarization / certification requirement;
- attachment class;
- portal/form field, when the buyer actually specifies one;
- source section coordinate.

The compiler never invents an absent filename, portal field, signatory authority, notarization/certification, price, or due time. A later generation is the active source snapshot; the manifest also records exact field-level changes from the immediately preceding generation so superseded instructions are visible to the owner.

## Artifact custody

Candidate artifacts bind an artifact id, current slot id, safe relative path, retained SHA-256, format/page metadata, and optional evidence attestations. The CLI reads the actual bytes from `--artifact-root` and requires:

- a real artifact root directory, not a symlink;
- a safe relative path that stays under that root;
- a regular file (symlinks/FIFOs/special files are rejected before open);
- a bounded byte count;
- stable dev/inode/size/mtime/ctime during the read;
- an exact SHA-256 match to the retained artifact record.

Signature/notarization/certification attestations must bind the exact candidate artifact SHA-256. They prove only that retained evidence exists; they never authorize a signature/certification action or claim the signer is authorized.

## Outputs

Compile creates, exclusively:

- `assembly.json` — canonical source/artifact/slot state, active generation, amendment delta, status, conflicts, missing worklist, and hard-false authority;
- `assembly.md` — human owner checklist;
- `receipt.json` — canonical input/source-history/output digests and the same hard-false authority ceiling.

`verify` recompiles all three outputs from the exact retained input plus artifact bytes. Rehashing a tampered manifest is not enough: semantic replay must reproduce every byte.

## Strict input behavior

The JSON parser rejects duplicate keys, floating/non-finite numbers, unknown/missing keys, bool-as-int aliases, non-NFKC text, Unicode control/format characters, unsafe paths, duplicate identities, invalid timestamps, and unbounded collections. Source observations must be strictly increasing in both sequence and time. Future source observations fail closed.

## Authority ceiling

Every manifest and receipt hard-code false for buyer contact, portal login/upload, form submit, signature/certification action, pricing commitment, proposal submission, contract/award establishment, payment action, receivable, and revenue.

`ASSEMBLY_READY_FOR_OWNER_REVIEW` therefore means exactly that: **ready for owner review**, not submitted, accepted, awarded, billable, paid, or revenue.

If a human later chooses to submit, that is a separate action requiring fresh collision/DNR control and any applicable single-writer arbitration immediately before external mutation.

## Synthetic run

The checked-in fixture is synthetic and asserts no real buyer, bid, award, payment, or revenue fact.

```bash
TMP="$(mktemp -d)"
python -m revenue.procurement_solicitation_ingest.submission_assembly compile \
  --input revenue/procurement_solicitation_ingest/submission_assembly/fixtures/synthetic_input.json \
  --artifact-root revenue/procurement_solicitation_ingest/submission_assembly/fixtures/artifacts \
  --out-dir "$TMP/out"

python -m revenue.procurement_solicitation_ingest.submission_assembly verify \
  --input revenue/procurement_solicitation_ingest/submission_assembly/fixtures/synthetic_input.json \
  --artifact-root revenue/procurement_solicitation_ingest/submission_assembly/fixtures/artifacts \
  --manifest "$TMP/out/assembly.json" \
  --checklist "$TMP/out/assembly.md" \
  --receipt "$TMP/out/receipt.json"
```

The root bridge `test_procurement_submission_assembly.py` executes the hostile suite under normal Python and `python -O`. The existing Commons `tests.yml` path filter already covers `revenue/procurement_solicitation_ingest/**`, so this package is path-scoped without consuming an additional workflow slot.
