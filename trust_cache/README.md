# trust-cache

**Proof is cached. Build unless the bytes moved.**

`host/trust_cache.py` is the first executable slice of
[TRUST AFTER PROOF](../ground/TRUST.md). It hashes the actual artifact and
keys passed checks by `(artifact_sha256, check_id)`.

```sh
python3 host/trust_cache.py status ARTIFACT CHECK_ID
python3 host/trust_cache.py run ARTIFACT CHECK_ID -- COMMAND ...
python3 host/trust_cache.py waste-count
```

The default ledger is `trust_cache/receipts.jsonl`. It is created on first
run and only appended to. Each line has exactly five fields:
`artifact_sha256`, `check_id`, `result`, `recorded_at`, and `evidence`.
The schema version lives inside `evidence`, so the cheap canary can reject
drift without adding a sixth receipt field.

- `UNVERIFIED`: no passing receipt for this hash/check pair; run.
- `TRUSTED`: the current bytes already passed; skip and build.
- `STALE`: this check passed older bytes; run on the new hash.
- `WASTE`: event recorded when a rerun of a trusted pair is attempted.

Commands run without a shell. Captured stdout/stderr are represented by hashes
in the receipt, not copied into the ledger.
