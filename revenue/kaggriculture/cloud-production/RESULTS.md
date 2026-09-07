# Development results

Candidate SHA-256: `cd414980637d8bfec9b5b445fe68315f70a30e1c1d9fd9c99ee141cbe0ebdc31`

| Opponent | Games | Wins | Mean margin |
| --- | ---: | ---: | ---: |
| KAG-COMPOSE `dispatch_balanced`, seed 9200017 | 2 | 2 | +21,501.5 |
| Merged KAG-PRODUCTION, seeds 9200047/81 | 4 | 4 | +8,120.0 |
| Kaito v43, seed 9200017 | 2 | 0 | -22,541.5 |
| Igor MultiRoute, seed 9200017 | 2 | 0 | -21,259.0 |
| Kaito v43, seeds 9200047/81 | 4 | 0 | -21,415.5 |
| Igor MultiRoute, seeds 9200047/81 | 4 | 0 | -27,495.75 |

All 20 scheduled selected-policy games completed without agent failure. Each
report's first-game reproducibility replay matched terminal scores and trace.
Seeds `9200017`, `9200047`, and `9200081` are development-only. Kaito and Igor
are pinned public references, not the September 7, 2026 leaderboard leader.

The exact feed-before-seed correction was rejected at 0/2 and -14,139 mean
against the merged policy. The promoted policy instead books seeds first,
decrements their fixed cost, then prices each WHEAT fill sequentially while
preserving 30 cash. ROWAN's next-day refresh contract replaces the former
current-age fertilizer calculation: tomato events end at ages 8/9/10/11,
fertilizer targets only uncovered future refreshes, and late un-cashable crop
events are excluded.
