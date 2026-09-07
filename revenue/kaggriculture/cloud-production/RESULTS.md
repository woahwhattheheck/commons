# Development results

Candidate SHA-256: `0fbe51eea32be64a2441c60ba7867d532614812cbb9823bbc9087fb6aecdd7d5`

| Opponent | Games | Wins | Mean margin |
| --- | ---: | ---: | ---: |
| KAG-COMPOSE `dispatch_balanced`, seed 9200017 | 2 | 2 | +21,501.5 |
| Merged KAG-PRODUCTION, seeds 9200047/81 | 4 | 4 | +8,120.0 |
| Kaito v43, seed 9200017 | 2 | 0 | -22,541.5 |
| Igor MultiRoute, seed 9200017 | 2 | 0 | -21,259.0 |
| Kaito v43, seeds 9200047/81 | 4 | 0 | -21,415.5 |
| Igor MultiRoute, seeds 9200047/81 | 4 | 0 | -27,495.75 |
| Shipped KAG-PRODUCTION, seeds 9200131/157 | 4 | 2 | +5,315.75 |
| Kaito v43, seeds 9200131/157 | 4 | 0 | -36,309.5 |
| Igor MultiRoute, seeds 9200131/157 | 4 | 2 | -19,282.75 |

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

The successor makes crop capacity responsive to current workers and observable
service load. Its separate labor-throttling arm lost 0/2 and -7,888 mean on
seed `9200131`, so those labor bytes were removed rather than bundled with the
winning crop-cap change. The crop arm's Kaito regression is retained above;
selection used paired checkpoint margin and the better worst strong-reference
gap, not a claim of universal improvement.
