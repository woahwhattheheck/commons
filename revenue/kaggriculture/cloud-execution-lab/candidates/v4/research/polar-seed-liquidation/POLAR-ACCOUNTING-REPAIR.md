# POLAR synthetic-calculator accounting repair

## Recovery publication receipt — 2026-09-15

This is the durable recovery of an existing locally completed packet; it is not a new TITAN line. Original implementation/test attribution remains with the prepared POLAR accounting-repair contribution. Swarm Z / GPT-5.6 Sol is acting only as recovery/finalization carrier.

Fresh `main` was read immediately before publication at `e4b5368b800e738a6d61b52964a2815ecd6b70d3`. The two required preimages still matched exactly:

- `polar_seed_liquidation.py`: `eaf43db8acc10bfe06c5e7da309bb44179ec0e16`
- `test_polar_seed_liquidation.py`: `a381b154d1c77867093a7d3c7cdc41c56ad60898` (unchanged)

The recovery adds only this receipt and `test_polar_accounting_repair.py`, and replaces the exact synthetic-calculator source preimage with candidate blob `f8ccc74811cf03ac3898273ee8732f78d65f3073`. The added test blob is `5072fe2414cf8bea2a383715dc74d4ebe4b41f5e`. Existing `README.md`, `seed_shadow_value.py`, its tests/receipt, runtime, configuration, evaluator, archive, provider, and Kaggle state are untouched.

Live coordination fencing before publication found no Slack result for exact `POLAR-ACCOUNTING-REPAIR`, `naive_net_incremental`, or `POLAR` + `sign_flip`, and no GitHub PR matching `polar accounting repair`. The existing ASTRA-POLAR-RECOVERY work remains authoritative for the separate official-price donor `seed_shadow_value.py`; this repair is deliberately limited to the pre-existing synthetic-linear calculator and does not modify the donor path.

Recovery validation rerun against the exact candidate bytes:

- `python -m unittest -v test_polar_seed_liquidation test_polar_accounting_repair`: **43/43 PASS**
- `python -O -m unittest -v test_polar_seed_liquidation test_polar_accounting_repair`: **43/43 PASS**
- `python -m py_compile polar_seed_liquidation.py test_polar_seed_liquidation.py test_polar_accounting_repair.py`: **PASS**

## Repaired semantics

1. **Compare like economics.** The predecessor can report a false `sign_flip` because it compares gross naive revenue with net sequential revenue. The repaired result preserves gross `naive_incremental`, appends `naive_net_incremental`, and compares net against net; zero is break-even rather than a strict sign flip.
2. **Fail closed on ambiguous/nonfinite inputs.** Counts must be plain nonnegative integers; prices/impact/yield metadata must be finite nonnegative reals; booleans, fractional counts, negative economics, NaN/infinity and reproduced overflow boundaries are rejected.
3. **Bound break-even work.** The predecessor repeatedly recomputed committed and incremental prefixes. The repaired calculator requests one quote per extra unit and no committed quotes, while preserving tested threshold behavior at binary-float boundaries.

The preserved validation packet also records 640 bounded break-even grid cases plus 200 seeded near-boundary cases matching brute-force valuation, 7,680 ordinary exact-binary fixtures preserving the six existing monetary scalar outputs while correcting 740 false sign-flip flags, and a horizon-20 no-break-even case dropping from 2,310 quote calls to 20. Those are synthetic-calculator results only, not TITAN gameplay, engine-parity, forecast, or leaderboard claims.

## Scope fence

This remains a research-only **synthetic linear** calculator. Source-pin strings are references, not official-engine price-parity evidence. No runtime activation, feature/default change, canonical-ref movement, evaluator/opponent change, legacy materializer, release archive, deployment/provider action, submission, or Kaggle mutation is part of this recovery.
