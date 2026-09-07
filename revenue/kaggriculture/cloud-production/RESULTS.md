# Development results

Candidate SHA-256: `e96735d6d4656030b79e0835f0d00d5d760cc28e9e5f0141e7fb50bd912568bb`

| Opponent | Games | Wins | Mean margin |
| --- | ---: | ---: | ---: |
| KAG-COMPOSE `dispatch_balanced` | 2 | 2 | +9,793.5 |
| Kaito v43 public reference | 2 | 0 | -41,809.0 |
| Igor MultiRoute public reference | 2 | 0 | -37,738.5 |

All six scheduled games completed without agent failure. The report's first
game reproducibility replay matched both terminal scores and trace SHA-256.
Seed `9200017` is development-only. Kaito and Igor are pinned public references,
not representations of the September 7, 2026 leaderboard leader.

Early discarded overlays were not widened after their one-seed rejection. They
are excluded from the selected artifact because they disrupted inherited
routes. The integrated dispatcher is the first promoted checkpoint.

