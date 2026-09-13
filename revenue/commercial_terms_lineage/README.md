# Commercial Terms Exception Lineage

`commercial_terms_lineage` is an offline, fail-closed commercial review primitive for live pursuits. It solves a narrow but expensive problem: a proposal can be technically ready while a buyer's base terms, required forms, Q&A, or addenda still contain unresolved commercial positions. The package makes the active source/term universe and every owner decision content-addressed so a later addendum cannot silently inherit stale approval.

## Trust model

The **authority packet is retained separately from the review input**. It is an operator-trusted root for the current source generation and complete active term universe. The compiler does not authenticate the buyer provenance of that root: if an untrusted actor can replace the retained authority file, no trust claim is made. Production file ingress binds the opened descriptor to the checked path generation before parsing. The review input cannot add, remove, or rewrite buyer terms by recomputing its own checksum. Generation 2+ must bind the canonical normalized authority SHA-256 (`authority_sha256(previous_authority)`) of the immediately preceding authority packet; source/term list ordering is not semantic.

Each active term carries a stable ID, category, exact clause digest, mandatory bit and source binding. Generation lineage is explicit:

- `NEW` — no predecessor with that identity;
- `CARRY_FORWARD` — same ID and exact same clause digest;
- `REVISED` — same ID, changed digest, and exact prior digest;
- disappeared prior terms require an explicit `BUYER_REMOVED` or `REPLACED` retirement row.

That means a changed MFN, audit, insurance, data/security, public-records, IP, payment or other clause cannot retain an old decision merely because its term ID stayed the same.

## Owner decisions

Decisions are separate evidence records bound to:

- opportunity;
- source generation;
- term ID + exact clause digest;
- decision ID/type;
- canonical decision time;
- evidence SHA-256.

A prior-generation decision can survive only for a `CARRY_FORWARD` term. Revised/new terms require current-generation decisions. Cross-opportunity decisions, stale generations, changed digests, future decisions and expired decisions fail closed or reopen owner review.

Supported decision types are `ACCEPT_AS_WRITTEN`, `EXCEPTION_REQUESTED`, `NOT_APPLICABLE`, and `HOLD`. Absence of a valid decision becomes `OWNER_DECISION_REQUIRED`; it is never inferred from free text.

## Certification fence

A review declares one posture:

- `NO_EXCEPTIONS_CERTIFICATION_REQUIRED`
- `EXCEPTIONS_MAY_BE_DISCLOSED`
- `TERMS_POSTURE_NOT_YET_KNOWN`

An exception plus a no-exceptions certification is a mechanical `CONFLICT`. Disclosable exceptions produce an exact exception manifest. Unknown certification posture or uncovered terms cannot reach terms-clear status.

The strongest state, `TERMS_CLEAR_FOR_OWNER_SUBMISSION_REVIEW`, means only that the supplied evidence is internally coherent for owner review. It is not legal advice and grants no contact, exception-request, pricing, certification, signature, contract, portal, submission, spend, payment, accounting or revenue authority.

## CLI

From this directory:

```bash
python cli.py compile-current \
  --authority authority.json \
  --review review.json \
  --output-json receipt.json \
  --output-markdown receipt.md

python cli.py verify \
  --authority authority.json \
  --review review.json \
  --receipt receipt.json
```

For generation 2+, pass `--previous-authority previous-authority.json` to both commands. Production package/CLI calls use `runtime.compile_current()` / `runtime.verify_current()` and own current UTC internally; they expose no caller time override. `lineage.py` is the deterministic engine used for tests/historical reconstruction and accepts an explicitly trusted time. Verification historically recompiles at the receipt's bound `compiled_at` and rejects a future-issued receipt against process-owned current UTC.

Production input reads are bounded, strict UTF-8, ordinary non-symlink files; runtime ingress binds lstat→opened `(dev, ino)` identity and rejects descriptor-generation changes during the read. Outputs are create-exclusive, short-write-safe ordinary files and never overwrite an existing path.

## Tests

```bash
python -B -m py_compile lineage.py runtime.py cli.py test_lineage.py test_runtime.py
python -B -m unittest -v test_lineage.py test_runtime.py
python -O -B -m unittest -v test_lineage.py test_runtime.py
```

The hostile suite covers addenda revision invalidation, exact carry-forward, new terms, explicit retirement, source completeness/review/freshness, certification contradictions, cross-opportunity replay, stale/future decisions, duplicate keys, strict types, malformed source identity, input ordering, receipt tamper, file overwrite/symlink refusal, and a synthetic multi-pursuit set spanning MFN, public-records/confidentiality, audit, insurance and data/security.
