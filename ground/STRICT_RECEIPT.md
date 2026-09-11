# Strict receipt validation

`host/strict_receipt.py` implements visibility-plan D3 as a shared fail-closed validator for experiment receipts. It does **not** choose a panel, fetch canonical state, or decide whether an experiment wins. The caller supplies the literal requested panel and the live canonical SHA at validation time.

A valid receipt must satisfy all of these together:

- Its embedded panel is byte-semantically equal to the caller's literal `seeds` and `opponents` lists, including order.
- Seeds are strict integers; Python booleans are rejected rather than coerced to `0/1`.
- Every score is finite; NaN and Infinity are rejected at JSON parse time and again for direct Python callers.
- Duplicate JSON keys are rejected by the parser. Duplicate `(seed, opponent)` cells are rejected while consuming the sequence, **before** a dictionary/index could overwrite one.
- Cells are exactly the cartesian product `seeds × opponents`: no missing pairs, no extras, no merely-equal row count.
- The receipt's `canonical_sha` exactly matches the caller-supplied live canonical SHA. A stale receipt fails rather than being relabelled current.

`fixtures/strict_receipt_poison.json` is an executable poison catalog covering bool seeds, duplicate cells, missing cells, extra cells, stale canonical identity, and literal-panel substitution. `test_strict_receipt.py` applies each mutation and requires fail-closed behavior.

CLI example:

```bash
python host/strict_receipt.py receipt.json \
  --requested-panel requested-panel.json \
  --live-canonical-sha "$LIVE_CANONICAL_SHA"
```

The CLI prints only the normalized validated receipt. A successful parse is evidence that the supplied receipt obeys this contract; it is not proof that the caller supplied the correct live SHA or that any remote artifact was independently downloaded.
