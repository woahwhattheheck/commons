# TITAN V3 S02 — paired-dominance admission firewall

Operation: `titan-v3-s02-admission-firewall-20260909-solpro`

This packet repairs the **admission mechanism**, not the leaderboard claim. The
merged S02 experiment ran each candidate only on simulated transition zero,
forced the candidate farm to PASS for the remaining horizon, scored absolute
cash, wrote `last_rival = PASS`, reused one mutable rival TITAN shadow across
candidate siblings, and allowed HIRE/SELL/HARVEST deletion or mutation. Its
recorded H=6 smoke lost all four games to Arlene with mean margin `-88615.5`
and paired own-cash deltas from `-88183` to `-108267`.

The replacement is fail-closed:

1. canonical action is always first and always remains the default output;
2. candidates may only permute the exact existing market rows;
3. farmer/hands, all non-market fields, every order payload and quantity, row
   multiplicity, and empty-row multiplicity are immutable;
4. action/state identity uses typed canonicalization, so raw-distinct keys such
   as integer `1` and string `"1"` cannot collide;
5. baseline and candidate use fresh one-step engine states with the same pair
   seed; there is no fictional multi-step PASS suffix or shared rival shadow;
6. scenario enumeration is uniquely named, deadline-aware, and raw-pull bounded;
7. empty rival private and hidden end-of-day RNG are labeled sensitivity-only,
   never exact evidence, even when their numerical delta looks favorable;
8. an executable recommendation requires complete, source-certified exact,
   state-equivalent paired scenarios and strict cash dominance in every case;
9. `TITAN_MPC_MODE=shadow` is the default; and
10. the full-game panel validator requires an explicit expected schedule and
    rejects missing whole cells, missing variants, unexpected cells/variants,
    duplicates, failures, one-seat panels, mean/W-L regressions, and any
    disallowed worst-pair regression.

## Verification

```bash
python -m py_compile planner_mpc.py main.py canonical_main.py \
  validate_panel.py test_planner_mpc.py test_validate_panel.py benchmark_guard.py
pytest -q
python validate_panel.py s02_observed_smoke.jsonl \
  --schedule S02-OBSERVED-SCHEDULE.json --min-pairs 4 \
  --output S02-OBSERVED-VERDICT.json
python benchmark_guard.py --iterations 5000 --output BENCHMARK.json
```

The validator command is expected to exit `2`: it is a machine-readable,
exact-schedule NO-PROMOTE receipt for the historical S02 H=6 smoke.

## Integration boundary

Do **not** replace canonical TITAN with this packet from unit evidence. A live
competition observation lacks the rival private packet needed to certify a
reacting exact transition, and end-of-day RNG is also hidden at the boundary.
The default scenario is therefore a diagnostic sensitivity world only. Keep
shadow mode unless an owner supplies source-bound offline evidence and then
passes an exact-current, process-isolated, both-seat official-engine development
and held-out panel. Promotion remains gated on the schedule-bound validator and
canonical archive/build checks.
