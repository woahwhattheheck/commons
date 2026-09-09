# SOL-CROOK — same-tile pasture HARVEST contention

Experimental, additive V3 candidate. Canonical runtime, configuration, archive, and submission bytes are untouched.

## Exact defect

Kaggriculture executes farmer then hands in index order. `HARVEST` acts on the worker's current tile, transfers the complete yield, and sets `yield_units` to zero. If multiple selected workers are stacked on one ripe pasture and all emit `HARVEST`, every actor after the first silently no-ops.

P07 joint-actor assignment is deliberately not reused: it rejects shared pickup tiles as stock contention. This lane handles only the already-selected same-turn collision.

## Guard

For each current tile, preserve the lowest-index `HARVEST`. Replace at most one later exact `HARVEST` with `CARE` only when all of these are true:

- the tile is a ripe COW or SHEEP pasture;
- the animal is already fed and not yet cared today;
- no selected worker on that tile already emits `CARE`.

CARE consumes no stock and does not move the worker. No witness returns the original selected object. Market rows and every unrelated unit action are exact.

## Focused verification

```bash
python -m unittest -v test_pasture_contention.py
```

The branch is an experiment, not a hosted-rating claim or automatic promotion signal. A paired current-TITAN control gate is required before any canonical integration.
