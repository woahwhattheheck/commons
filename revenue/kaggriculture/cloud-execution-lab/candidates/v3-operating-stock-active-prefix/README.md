# TITAN V3 operating-stock active-prefix candidate

This default-off candidate repairs one engine-boundary mismatch without changing
canonical TITAN policy files. The official interpreter truncates each raw market
queue to `market[:maxMarketOrdersPerTurn]` before parsing it. The enabled
operating-stock guard currently inspects several current and future market lists
without that boundary, so inert tail sales, hires, and purchases can alter its
fertilizer reservation decision or be rewritten despite never executing.

`active_prefix.py` gives the unchanged incumbent guard only executable market
prefixes, using a lazy route view, and restores the current action suffix exactly.
It refuses configurations above ten because one incumbent capacity helper is
independently certified only through its hard-coded ten-row bound. Invalid adapter
inputs return the exact parent action.

## Acceptance

From `revenue/kaggriculture/cloud-execution-lab`:

```bash
python candidates/v3-operating-stock-active-prefix/test_active_prefix.py
python test_operating_stock.py
python -m py_compile \
  candidates/v3-operating-stock-active-prefix/active_prefix.py \
  candidates/v3-operating-stock-active-prefix/candidate.py \
  candidates/v3-operating-stock-active-prefix/test_active_prefix.py
```

The focused suite includes predecessor-discriminating current-tail and
future-route cases, active-prefix controls, cap boundaries, suffix preservation,
input immutability, lazy-route behavior, and installation idempotence. Passing
contracts establish engine-prefix correctness only. They do not establish a game
score gain or authorize canonical integration, archive movement, or submission.
