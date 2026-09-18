# SOL-VERDANT — TITAN W10 realized fertilizer certificate

- Operation: `titan-frontier-W10-realized-fertilizer-certificate-20260909-02`
- Reviewed branch: `sol/verdant-w10-realized-fertilizer-certificate-20260909-03`
- Scope: additive observation/certification only
- Status: PR opened from the reviewed branch

## Receipt correction

The earlier Slack ship receipt that named PR `#11483` and commit `bda3ca568998ec26400465089273237c7255a41c` is invalid. Direct GitHub checks found that PR #11483 contains unrelated Super-MCP NavBuilds files, the named commit does not exist in this repository, the alleged branch does not exist, and the alleged W10 module was absent from `main`.

This operation therefore rebuilt W10 from a fresh branch and treats GitHub bytes as authoritative.

## Delivered paths

- `revenue/kaggriculture/cloud-execution-lab/analysis/w10-fertilizer-cycle/realized_fertilizer.py`
- `revenue/kaggriculture/cloud-execution-lab/analysis/w10-fertilizer-cycle/test_realized_fertilizer.py`
- `revenue/kaggriculture/cloud-execution-lab/analysis/w10-fertilizer-cycle/README.md`
- `.github/workflows/titan-w10-realized-fertilizer.yml`
- this receipt

No existing producer, evaluator, runtime, configuration, canonical archive, provider state, or Kaggle state was edited.

## Acceptance behavior

The checker returns `CERTIFIED` only for a paired deterministic experiment that has:

1. identical engine/evaluator/opponent/start-state/protocol/commitment identity;
2. identical starting metrics and capacities;
3. additional fertilizer use;
4. additional produced, harvested, deposited, and sold units;
5. an attributable incremental chain `produced >= harvested >= deposited >= sold > 0`;
6. milestone order `fertilizer -> production -> harvest -> deposit -> sale`;
7. positive final cash delta after in-horizon costs;
8. no new discarded output;
9. no protected-obligation regression; and
10. no protected-stock regression.

Unknown fields, booleans, non-integer counters, malformed hashes, nonmonotone cumulative values, capacity overflow, unaccounted actions, budget overflow, identity mismatch, start mismatch, and horizon truncation fail closed.

## Exact-byte verification

After publishing the reviewed branch, the module and test were fetched back through the public GitHub contents API, base64-decoded into a clean cloud directory, and tested from those readback bytes:

```text
python -m py_compile realized_fertilizer.py test_realized_fertilizer.py
python -m unittest -v test_realized_fertilizer.py
Ran 17 tests
OK
```

The hosted workflow repeats those commands on pull requests affecting the W10 paths.

## Meaning and boundary

This artifact closes the evidence-definition gap behind W10: a local yield quote is no longer enough to call fertilizer productive. It does **not** claim a live winning game or silently promote a producer change. The next owner must instrument the current producer/evaluator to emit the strict trace, run paired seed/opponent experiments, and admit behavior only from actual `CERTIFIED` results.