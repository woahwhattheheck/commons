# TITAN V3 final operating-stock prefix candidate

This default-off candidate repairs one engine-boundary mismatch without changing
canonical TITAN policy files. The official interpreter truncates the **final**
returned market queue to `market[:maxMarketOrdersPerTurn]` before parsing it.
The enabled fertilizer operating-stock guard currently inspects all rows in the
queue it receives, so a truly inert tail sale, hire, or purchase can alter its
reservation decision or be rewritten despite never executing.

## Why the first head was held

The first implementation at `d817c21d08ee58ec526dd4e8745cef12f3eb7d1a`
trimmed the queue at the guard's existing early call site. That was not sound:
canonical early-capital ordering runs later and stable-sorts the full market tape,
so a row that was in the raw suffix can become executable before return. The first
head was publicly self-held before its queued CI was treated as evidence.

## Correct boundary

`final_boundary.py` defers this candidate's early operating-stock call, lets the
canonical completed-action finalizer run early-capital plus final pressure, and
then invokes the unchanged incumbent guard once. `active_prefix.py` isolates only
the now-final current prefix and restores its suffix byte-for-byte.

Future raw route rows remain untrimmed and conservative because their later
market transformations have not run yet. Deadline-fallback finalization also
retains predecessor behavior and does not invent a deferred stock edit.
Every newly constructed runtime instance is patched independently, so controller
or entrypoint reconstruction cannot silently lose the candidate.

## Acceptance

From `revenue/kaggriculture/cloud-execution-lab`:

```bash
python candidates/v3-operating-stock-active-prefix/test_active_prefix.py
python test_operating_stock.py
python test_early_capital.py
python -m py_compile \
  candidates/v3-operating-stock-active-prefix/active_prefix.py \
  candidates/v3-operating-stock-active-prefix/final_boundary.py \
  candidates/v3-operating-stock-active-prefix/candidate.py \
  candidates/v3-operating-stock-active-prefix/test_active_prefix.py
```

The 18 focused contracts include predecessor-discriminating final-tail cases,
the live default ten-row witness, active-prefix controls, exact suffix and input
preservation, cap normalization, idempotent installation, fresh-instance
reconstruction, exception cleanup, deadline-fallback parity, and a composition
witness where early-capital promotes a raw tail HIRE into the executable prefix.
A pinned official `_process_market` transition proves a true final suffix is inert.

Passing these contracts establishes boundary correctness only. It does not
establish a game-score gain or authorize canonical integration, archive movement,
provider action, or competition submission. Complete paired both-seat games with
realized action/state attribution remain required for any strength claim.
