# OPS-DEDUP-THRESHOLD — measured cost of order-preserving dedup

`OPS-PERF-SCAN` reported 15 sites in the delivered kit written as
`seen = []` + `if x not in seen: seen.append(x)`, each with magnitude
**UNKNOWN**. This lane measures the cost curve so those findings carry a number,
and supplies a replacement that is safe to adopt without auditing each site.

Built by seat **OP5-OBSIDIAN** (Claude Opus 5). Companion to
`uiowa_rfq_18649_capacity_benchmark/` and `uiowa_rfq_18649_capacity_scan/`.

Every figure in `results/` was measured on this machine in one run.

## Run

Python 3 standard library only. No network.

```bash
cd revenue/uiowa_rfq_18649_dedup_threshold
python3 -m unittest discover -v
python3 bench_dedup.py
```

## Files

| File | What it is |
|---|---|
| `dedup.py` | Four order-preserving dedup strategies, including the recommended one. |
| `bench_dedup.py` | Measurement harness (`perf_counter` + `tracemalloc`, separate passes), crossover finder, report renderer. |
| `test_dedup_threshold.py` | 19 `unittest` tests. |
| `results/DEDUP_REPORT.md` | Generated report. |
| `results/dedup_results.json` / `.csv` | Full measurement record. |

## Measured result

Speedup over the current form, minimum of 7 repeats after a warmup:

| Distinct items | `dict_fromkeys` | `set_aside` | `ordered_unique` |
| ---: | ---: | ---: | ---: |
| 10 | 0.99x | 1.13x | 1.05x |
| 25 | 3.37x | 3.14x | 3.01x |
| 100 | 10.90x | 9.02x | 8.77x |
| 800 | 249.42x | 192.91x | 187.07x |
| 3,200 | 514.23x | 398.70x | 382.10x |

**Smallest measured n at which the O(n) forms are at least 2x faster: 25.**
That is the smallest point actually run, not an interpolation. At n=10 the
difference is within noise in both directions, so below roughly that size the
current form is fine and changing it buys nothing.

## The recommendation is not "use a set"

Measured by running each strategy on a list of dicts:

| Strategy | Works on unhashable input |
|---|---|
| `dict_fromkeys` | **NO** — `TypeError: unhashable type: 'dict'` |
| `set_aside` | **NO** — `TypeError: unhashable type: 'dict'` |
| `list_scan` (current) | yes |
| `ordered_unique` (recommended) | yes |

`dict_fromkeys` is the fastest and would break any site deduplicating dicts or
lists. `ordered_unique` takes the set fast path per item and falls back to a
scan across only the unhashable items, so it is a drop-in for the existing code
whatever the element type, at a small cost against `dict_fromkeys`.

## Output correctness

All four strategies must return each distinct item exactly once in **first-seen
order**, compared against the current `list_scan` behaviour before anything is
timed. The harness raises `SystemExit` if any strategy disagrees, and a test
swaps in a fast wrong answer to confirm that gate fires. A separate test asserts
the result is not merely `sorted(set(items))` — a rewrite that returns the right
items in the wrong order would pass a naive membership test and is broken for
these sites, which are building ordered output.

## UNKNOWN

- **The number of distinct items each of the 15 flagged sites actually sees.**
  That depends on University data this lane does not have. The curve is a
  decision aid against a known n; it is not a verdict on any site, and no site
  was profiled in place.
- Whether any flagged site is on a hot path at all.
- Whether any flagged site handles unhashable elements — not determined per
  site, which is why the recommended replacement handles both cases.

No lane, seat, or person is scored. This lane edits nothing outside itself; the
flagged sites belong to other seats and are left alone.
