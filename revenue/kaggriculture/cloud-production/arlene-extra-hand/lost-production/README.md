# Lost-production extra hand v2

Research checkpoint over the unchanged Arlene parent
`1dc166ae2bf0c56a44fac4482f469b8812968c4cb32459cb9860f5077897a7d4`.
It is separate from the rejected visible-yield v1 experiment.

The overlay hires at most one optional worker per day, and only when visible
engine state proves that a same-day harvest prevents animal-cap overflow or a
crop decay before Arlene's next scheduled harvest. HIRE spawn is projected
after current unit moves. The worker may finish anywhere because end-of-day
deposit is automatic; terminal-day work is excluded because terminal market
processing precedes that deposit.

`dated_allocation.py` is a bounded dependency-free executor. Shared stock is
earmarked once before each dated consumer; a market purchase becomes accessible
on the following action step, not to an earlier same-turn PICKUP. Optional jobs
use explicit start/end windows and non-overlap. No OR-Tools or Stockpyl runtime
dependency is introduced.

Development status: 12/12 games complete on seeds 9600421, 9600449, and
9600467, both seats versus intact Arlene and Apex. Own cash improved in all six
paired Arlene controls and all six paired Apex controls. Head-to-head was
5W/0T/1L against Arlene and 6W/0T/0L against Apex. This is promising research,
not a submission designation; no Kaggle upload or public notebook write was
made.

Build and focused test:

```bash
python build.py
python -m unittest -v test_executor.py
```

Exact compact evidence is in `results/development.json`.
