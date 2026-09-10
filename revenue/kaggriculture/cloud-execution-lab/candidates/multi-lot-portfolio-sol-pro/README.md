# TITAN V3 multi-lot SELL portfolio (SOL-PRO)

Candidate: `TITAN-V3-MULTI-LOT-PORTFOLIO-20260910-01`

## Hypothesis

Canonical `scheduler.py` evaluates every stocked non-operating product but
retains one scalar `best`; only that product can update `current` and
`self.planned` on a turn.  A second independently admitted all-scenario-positive
plan is discarded even when it fits inherited SELL rows or a distinct free
suffix order slot.

This candidate leaves target order, per-product optimization, rival scenarios,
rank semantics, inherited market indices, terminal handling, and the canonical
winner unchanged.  It composes extra plans only when their current-turn sale is
not below the pre-portfolio quantity.  A global allocator then gives each
product at most one finite appended-SELL slot, using the existing
`(forced_feasibility, worst_relative_gain)` rank and evaluation order for ties.
Any malformed/ambiguous candidate, plan, quantity, rank, or market row falls
back to the canonical scalar winner.

## Files

- `multi_lot_portfolio.py` — pure global slot allocator and diagnostics receipt.
- `candidate_patch.py` — exact transform bound to canonical scheduler Git blob
  `a483b24dd72b580d7d8811636b54d2d44f391575`.
- `candidate.py` — playable `candidate.py::agent` repository entrypoint.
- `build_candidate.py` — deterministic standalone `main.py::agent` tar builder;
  it never writes canonical archive or pointer paths.
- `run_panel.py` — exact-bound adapter over the existing provenance-complete
  paired official-engine collector.
- `test_*.py` — predecessor, malformed-input, exact-source, and build contracts.

## Promotion gate

The workflow records a paired development panel against unchanged canonical.
`ADVANCE` requires activated traces, positive mean own cash, nonnegative mean
margin, nonnegative mean own cash in every selected opponent stratum, and no
cell below -500 own cash.  This is only a development gate, never a leaderboard
or Kaggle claim.  No canonical source, config, archive, pointer, provider, or
submission is mutated by this lane.
