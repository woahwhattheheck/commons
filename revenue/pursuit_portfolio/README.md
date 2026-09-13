# Pursuit Portfolio Allocation

`pursuit_portfolio` is an offline owner-review control for a problem that only appears once outreach and procurement discovery start working: several opportunities can be individually credible at the same time while the owner still has finite proposal, research, engineering, and partner-development capacity.

The compiler consumes **already-reviewed upstream pursuit evidence** plus an explicit owner capacity policy. It chooses an exact, deterministic feasible subset. It does not estimate win probability, expected revenue, buyer intent, pricing, staffing, or whether a bid should be submitted.

## What it answers

Given:

- upstream states `READY`, `CURABLE`, `HOLD`, or `TERMINAL`;
- immutable upstream/source digests and evidence timestamps;
- an official response deadline or explicit `NO_DEADLINE`;
- integer owner `priority_units` (preference, not economic value);
- positive pursuit effort units by opaque capacity pool; and
- owner-declared available/reserve units per pool,

it returns:

- `ALLOCATED_READY` for upstream-ready rows selected by the exact portfolio optimum;
- `CURABLE_RECOVERY_ALLOCATED` when owner capacity is allocated to an explicitly still-curable row;
- `DEFERRED_CAPACITY` for an otherwise eligible row outside the optimum;
- `HOLD_UPSTREAM`, `TERMINAL`, `DEADLINE_BUFFER_BREACHED`, or `HOLD` for rows that cannot enter allocation;
- exact available/reserve/usable/allocated/headroom facts per pool; and
- for a capacity-deferred row, the additional units in each currently limiting pool that would make that row individually fit against the incumbent residual headroom.

That counterfactual is intentionally narrow. It does not assert that increasing capacity preserves the same globally optimal portfolio.

## Exact objective and bound

At most **20 allocatable candidates** enter the exhaustive solver. This hard bound permits an exact certificate over at most `2^20` subsets instead of silently returning a heuristic. Larger portfolios must be split by an owner planning horizon or otherwise reduced upstream.

The objective is lexicographic and public:

1. maximize total explicit owner `priority_units`;
2. maximize number of allocated opportunities;
3. minimize total pursuit effort units;
4. choose the lexicographically smallest opportunity-ID tuple.

There is no hidden score, ratio, probability, LLM ranking, expected-value model, or revenue forecast.

## Policy binding

`policy.policy_sha256` must equal SHA-256 of canonical JSON for the normalized policy object **without** `policy_sha256`:

```json
{"evidence_max_age_seconds":86400,"horizon_end":"2026-09-20T00:00:00Z","horizon_start":"2026-09-13T00:00:00Z","pools":[{"available_units":24,"pool_id":"proposal","reserve_units":4}],"revision":1,"schema":"pursuit-portfolio-allocation/policy/v1"}
```

Canonical JSON is UTF-8, sorted keys, no spaces, and one trailing newline. This makes silent capacity-policy edits detectable.

## CLI

```bash
python -m revenue.pursuit_portfolio.cli compile portfolio-input.json out/portfolio-review
python -m revenue.pursuit_portfolio.cli verify out/portfolio-review
```

Production `compile` samples current UTC itself. Core tests and deterministic replay may pass a trusted explicit `evaluated_at`; the compiled packet records that instant and embeds the normalized input so `verify` can recompile exact bytes.

Publication is create-exclusive. Existing output paths and final-component symlinks are refused. Inputs are bounded regular UTF-8 JSON files with duplicate-key, float/non-finite, bool-as-int, unsafe-integer, malformed-hash/time/ref, and future/stale-evidence rejection.

## Authority ceiling

This module is **offline owner portfolio decision support only**. It performs no buyer/partner contact, email/SMS/DM/call, registration, question submission, portal mutation, proposal/bid submission, pricing, staffing assignment, scheduling, signature/certification, contract acceptance, spend, invoice/payment/refund/bank action, award claim, buyer-intent inference, probability/forecast, cash assertion, or recognized-revenue action.

`ALLOCATED_READY` only means an upstream-ready opportunity fits the supplied owner planning constraints at the recorded evaluation time.
