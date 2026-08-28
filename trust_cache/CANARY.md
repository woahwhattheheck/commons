# trust-cache live canary

**Proof is cached. Build unless the bytes moved.**

v1 (`host/trust_cache.py`) is the ledger. This file is the next slice: a
cheap always-on canary over a named input set, with full checks only for
`UNVERIFIED` or `STALE`.

```sh
python3 host/trust_cache_canary.py --ledger LEDGER canary \
  --input host/trust_cache.py --input test_trust_cache.py \
  --check-id trust-cache-unit

python3 host/trust_cache_canary.py --ledger LEDGER run \
  --input host/trust_cache.py --input test_trust_cache.py \
  --check-id trust-cache-unit \
  -- python3 test_trust_cache.py
```

The canary hashes **actual file bytes**. A JSON summary is not a receipt
and cannot make a pair `TRUSTED`. Malformed ledger rows fail closed.

CI: `.github/workflows/trust-cache.yml` restores the append-only JSONL,
runs the canary every time, and skips a `TRUSTED` pair (recording `WASTE`)
until an input byte moves.
