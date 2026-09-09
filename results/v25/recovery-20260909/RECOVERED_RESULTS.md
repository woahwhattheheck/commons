# Recovered v25 sim results (2026-09-09)

Candidate: TITAN V2 archive `6705147ba96fe4c6c3762197f024ff1d47d38004f03d0059055ef4467bb5b88e`
Engine: official kaggle-environments 1.32.7 (upstream 28b6d8af), engine bytes pinned in `runner/setup.sh`
Panel: arlene, apex, kaito_v43, cok_v10, public_bt12, v1_submitted (Panel B adds `starter`), both seats

## 1. Parent session panels (fully recovered)

Source: Slack #claude-containment-board, 2026-09-09 06:11:58 EDT,
https://tokenjunkielabs.slack.com/archives/C0BUH19DW80/p1788948718027199
(posted by the "V2 simulations setup" session, session_01PJzDkwuT5UKKnAHNNjBTjX)

### PANEL A — seeds 2609200001–2609200080 × 6 opponents × 2 seats
960 scheduled · 960 completed · 0 errors · 0 timeouts · wall 1002 s · 57.5 games/min · 8 shards

| opponent | games | W | T | L | mean margin |
|---|---:|---:|---:|---:|---:|
| cok_v10 | 160 | 160 | 0 | 0 | 22657.3 |
| public_bt12 | 160 | 160 | 0 | 0 | 23040.3 |
| arlene | 160 | 159 | 0 | 1 | 1244.0 |
| apex | 160 | 158 | 0 | 2 | 7985.6 |
| v1_submitted | 160 | 157 | 0 | 3 | 740.4 |
| kaito_v43 | 160 | 156 | 0 | 4 | 17500.4 |
| **TOTAL** | **960** | **950** | **0** | **10** | |

Both-seat losses (3): apex seed 2609200002 (−2468); kaito_v43 seed 2609200020 (−314); kaito_v43 seed 2609200024 (−201)

### PANEL B — seeds 1909090901–1909090950 × 7 opponents × 2 seats
700 scheduled · 700 completed · 0 errors · 0 timeouts · wall 854 s · 49.2 games/min

| opponent | games | W | T | L | mean margin |
|---|---:|---:|---:|---:|---:|
| cok_v10 | 100 | 100 | 0 | 0 | 22447.0 |
| public_bt12 | 100 | 100 | 0 | 0 | 25084.5 |
| starter | 100 | 100 | 0 | 0 | 154093.4 |
| arlene | 100 | 99 | 0 | 1 | 1360.5 |
| v1_submitted | 100 | 98 | 0 | 2 | 858.4 |
| kaito_v43 | 100 | 96 | 0 | 4 | 16535.3 |
| apex | 100 | 94 | 0 | 6 | 7539.8 |
| **TOTAL** | **700** | **687** | **0** | **13** | |

Both-seat losses (4): apex 1909090904 (−4738); kaito_v43 1909090922 (−1961); kaito_v43 1909090944 (−1231); apex 1909090937 (−815)

vs v1_submitted over 260 games: mean +795.9, median +715.0
S23 identity check: workers 1 vs 8 → 36/36 games byte-identical
Throughput (games/min): serial 6.7 · w4 47.4 · w6 61.5 · w8 63.9 · w12 64.3

## 2. Child shard sessions (summaries recovered; raw files still in the containers)

Sim shards ran `run.sh <SEED_START> 60 <OUTDIR>` → 720 games each. Cloud shards ran 8 seeds → 96 games each.
Seed ranges per shard were assigned by the parent session and are recorded only in each shard's transcript and `meta`;
they are not in the session records.

| session | status | games | failed | games/min | note |
|---|---|---:|---:|---:|---|
| v25 sim shard A | archived at start | – | – | – | no run recorded |
| v25 sim shard B | completed | 720 | 0 | – | SUMMARY.json shown in transcript |
| v25 sim shard C | completed | 720 | – | – | SUMMARY.json shown in transcript |
| v25 sim shard D | completed | 720 | – | 50.71 | |
| v25 sim shard E | completed | 720 | – | 47.7 | |
| v25 sim shard F | did not run | – | – | – | asked for the full second command |
| v25 sim shard G | completed | 720 | – | 56.81 | |
| v25 sim shard H | did not run | – | – | – | waited for confirmation |
| v25 sim shard I | completed | 720 | 0 | 39.69 | 720/720 passed |
| v25 cloud shard R | completed | 96 | 0 | 51.3 | wall 112.3 s; apex 14/16, others 16/16 |
| v25 cloud shard S | completed | 96 | 0 | 44.94 | all wins |
| v25 cloud shard T | completed | 96 | 2 | 49.67 | 2 apex games failed (corrupt .so bridge) |
| v25 cloud shard U | completed | 96 | 1 | 61.94 | 1 apex failure; other opponents 16-0 |
| v25 cloud shard V | completed | 96 | 0 | 45.7 | wall 126 s |
| v25 cloud shard W | completed | 96 | 0 | 36.92 | wall 156 s; all 6 opponents swept 16-0 |
| v25 cloud shard X | completed | 96 | 0 | 45.69 | |
| v25 cloud shard Y | completed | 96 | 0 | 46.86 | wall 122.9 s |

Fire sessions (`v25-fire`, background `setsid nohup` runs logging to `/tmp/sim.log`):
launched 03, 04, 08, 09, 12, 14, 22 · did not launch 01, 02, 05, 06, 10, 11, 16, 17, 18, 20, 21 · no session 07, 13, 15, 19.

Completed games whose raw files are still inside the shard containers: 6 × 720 + 8 × 96 = **5,088**.
Session IDs for every row are in `sessions_index.csv`.
