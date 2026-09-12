# GANDER × STARVEORACLE — alternating-feed goose service

This package strengthens two corrected Gemini ideas inside the single existing V4 opening-expansion authority. It is research evidence, not a new controller or default.

## Composite result

Canonical GANDER certifies a feasible Day-0 frontier of **9 GOOSE + one HIRE**. Those geese are placed before EOD0 and become fertilizer-ready, but they also finish that refresh with `consecutive_unfed = 1` because they were not fed on placement day.

That detail changes the naive starvation story: **Day 1 cannot be skipped.** A second miss at EOD1 would make every goose escape. The safe source-bound cadence is therefore:

- Day 1: FEED + COLLECT_FERTILIZER all nine geese.
- Day 2: skip FEED; collect FERTILIZER.
- Day 3: FEED + collect FERTILIZER.
- Day 4: skip FEED; collect FERTILIZER and HARVEST EGG.
- Continue feed on odd days and skip on even days through Day 29.

The exact-interpreter composite uses GANDER's two-worker site partition and one fresh HIRE per service day. On mature skip-feed days, the nine freed FEED actions are spent on nine HARVEST actions while fertilizer collection remains daily. CARE is never used.

Across the remaining Day 1..29 service window, the constructed cadence:

- feeds on 15 days and skips on 14;
- consumes **135 WHEAT** instead of 261 under feed-every-day service, saving **126 WHEAT units**;
- saves the same **126 FEED action attempts**;
- preserves all 9 geese with maximum observed unfed streak 1;
- realizes the full base-production outer count of **243 EGG = 9 × 27** with no held-EGG clipping;
- realizes **270 FERTILIZER = 9 × 30**, counting the final pending EOD fertilizer;
- keeps observed per-goose held EGG at at most 2, below the engine `max_held = 4`;
- fits both feed-day and skip-day routes in the post-HIRE daily unit window with the same two-worker geometry.

These are mechanism/action/wheat-unit results. They are **not cash or terminal-margin results**: WHEAT acquisition price, EGG/FERT sale timing, shed pressure, CARE opportunity cost, rival behavior, town demand and displaced opening work are not priced here.

## Route-capacity dividend

The alternation is more than a WHEAT discount. Under the exact canonical GANDER two-worker partition and the 23 unit-action slots remaining after the daily HIRE:

| service | main farmer | hired hand | fits both? |
| --- | ---: | ---: | --- |
| FEED + FERT | 20 | 21 | yes |
| skip FEED + FERT + HARVEST | 19 | 20 | yes |
| FEED + FERT + HARVEST | 25 | 25 | **no** |

So an all-nine same-day full service pass cannot be performed by these two workers when FEED is retained; each route is two actions over the available window. Removing FEED on the safe alternating days makes the all-nine EGG harvest fit while still collecting every FERT. This does not prove that no more complex rotating-harvest schedule could work under daily feeding, but it proves the direct full-service route that the composite replaces is infeasible and quantifies the capacity created by the skip.

## Why this is stronger than either input alone

STARVEORACLE proves that an unfed-but-surviving goose still receives base EGG production and fertilizer, but it does not prove a nine-goose live route can service the next feed and realize output in time. GANDER proves the nine-goose geometry and daily FEED/FERT route, but it pays the full WHEAT/action load.

The composite closes that gap. GANDER supplies the route and post-EOD0 state; STARVEORACLE supplies the one-miss production theorem; the freed feed slot supplies the missing EGG collection capacity on skip days. The resulting cadence satisfies the starvation admission conditions mechanically while remaining explicit about CARE and economics.

## Predecessor killer

`gander_starve_cadence.py` also executes the historical naive phase that skips Day 1. Because EOD0 already created the first unfed strike, all geese escape at EOD1. This boundary is pinned in tests so a future refactor cannot silently shift the alternating phase and resurrect the bad literal rule.

## Source custody

The composite authenticates every executable helper **before importing it**, then consumes the exact official engine:

- official engine Git blob `3c202c7ee921da239356789e266b694635103fc4`;
- official engine SHA-256 `bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e`;
- GANDER helper `goose_printer_oracle.py` Git blob `38ae7715c233c74f24aacd5fe09f4d0d7a630037`;
- STARVEORACLE helper `starvation_cadence.py` Git blob `8831ff953faf033cc6d3892c6f32ccd1ee1af06c`.

Only after both helper blobs match does the composite execute them. GANDER supplies site geometry and authored Day-1 route counts; STARVEORACLE supplies exact-engine loading and intermittent-feed semantics. The simulator then starts at the exact semantic post-EOD0 GANDER boundary and runs the official interpreter for every callback from Day 1 through Day 29.

## Next gate

The gameplay/economics owner should consume this cadence through the existing opener/native scheduler, not a sibling controller. Run current-native both seats against current opponents and compare the incumbent opening with feasible GANDER counts under exact WHEAT acquisition and sale behavior. Record CARE displacement, shed occupancy, EGG/FERT realization and sale timing, fallback feed-deadline safety, natural engagement, and terminal margin.

Promotion requires positive paired terminal economics with no escape/storage/new-loss regressions. The 126-unit WHEAT saving and the two-worker route-capacity dividend are strong mechanism signals, not an activation decision.

## Validation

From this directory:

```bash
python test_gander_starve_cadence.py
python -O test_gander_starve_cadence.py
python gander_starve_cadence.py
```

The focused suite exercises the exact interpreter, the mandatory Day-1 feed predecessor, full nine-goose survival/output, held-cap safety, two-worker route fit and full-service overflow, pre-import helper custody, explicit CARE exclusion and exact engine identities.
