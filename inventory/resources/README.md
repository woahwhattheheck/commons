# Commons resource records

This directory is the append-only evidence journal behind the existing resource
ledger. It extends the ledger; it does not create a second resource truth.

- `ground/RESOURCE_LEDGER.json` is the canonical current-state projection.
- `ledger.html` is its human door.
- `inventory/resources/records/*.json` preserves dated census and transition
  evidence so later projections can explain why a state changed.
- `resources.json` remains the historical Court-grant register and must not be
  repurposed.
- `resources.html` remains the hand-readable resource directory and links to the
  ledger.

## Lifecycle contract

Every current resource has a `kind`, evidence-backed `capacity`, lifecycle
`stage`, operating `condition`, `holder`, `authority`, current `consumer`,
expected `value`, `next_action`, `last_used_at`, and `stale_after` boundary.

Stages advance monotonically only with evidence:

`DECLARED → AVAILABLE → REACHABLE → ASSIGNED → EXERCISED → PRODUCING`

Condition is independent. A resource can be reachable and held, exercised and
degraded, or producing and constrained. A subscription reset is capacity, not
permission. A cached connector is inventory, not capacity. A PRESENT actor is
an address until a fresh receipt proves liveness.

## Operating loop

1. Discover without exposing secrets or private content.
2. Verify with the smallest safe probe.
3. Assign an exact consumer and outcome.
4. Exercise it once.
5. Record the result and measured value.
6. Advance, hold, release, supersede, archive, or retire it.

Calls are not value merely because quota exists. Prefer a dormant resource only
when it advances a real Commons outcome. Bryce is a resource too: batch the
irreducibly owner-only decisions and protect owner attention from status churn.

Validate the projection with:

```bash
python3 host/resource_ledger.py --root .
python3 -m unittest -v test_resource_ledger.py
```

