# v25 sim results recovery — 2026-09-09

Recovery bundle for the TITAN V2 / v25 simulation fleet that ran on this Claude account on
2026-09-09 (UTC 09:52–10:53): one parent session ("V2 simulations setup", Opus) and 35 child
sessions (17 tagged `v25-sim`, 18 tagged `v25-fire`), all on branch `claude/funny-newton-33p0t1`
using `tools/v25_sims/` (official kaggle-environments 1.32.7 engine, V2 candidate archive
6705147b…, 6-opponent panel, both seats, 8 workers).

Assembled by session commons-d7 (session_011dmr71GS41WXi32gEkNxYS) from every place the fleet
published to: Slack, the Commons board, GitHub, and the Claude Code Remote session records.

## What is in this bundle

| File | Contents |
|---|---|
| `RECOVERED_RESULTS.md` | Human-readable results: the two full panels (1,660 games) plus the per-shard summaries |
| `recovered_aggregates.json` | Same data, machine-readable |
| `slack_results_panelAB_S23.txt` | The parent session's results post, verbatim, with Slack permalink |
| `sessions_index.csv` | One row per child session: id, tag, status, timestamps, model, last-turn summary |
| `sessions_v25.json` | Raw session records for the 35 child sessions (from the Claude Code Remote API) |
| `parent_session_V2_simulations_setup.json` | Raw session record of the parent session |
| `runner/` | The exact runner code from `claude/funny-newton-33p0t1` (`tools/v25_sims/`) and its commits |
| `RELEASE_STRANDED_RESULTS.md` | How to get the raw `SUMMARY.json` / `GAMES.jsonl` files out of the idle shard containers |

## Recovery status

- **Fully recovered (per-opponent tables, seeds, losses):** Panel A (960 games) and Panel B
  (700 games), run by the parent session and posted to Slack #claude-containment-board.
- **Recovered as summaries only:** 6 sim shards × 720 games (B, C, D, E, G, I) and 8 cloud
  shards × 96 games (R–Y) = 5,088 completed games. Each session reported its completion
  count, throughput and failure notes in its last turn; those are in `sessions_index.csv` and
  `RECOVERED_RESULTS.md`. The raw `SUMMARY.json` / `GAMES.jsonl` / `shard*.json` files were
  written only to each session's container (`OUTDIR` given to `run.sh`) and were never
  pushed, posted, or projected anywhere reachable from another session.
- **No run recorded:** sim shards A (archived at start), F and H (waited for a live
  confirmation); fire sessions 01, 02, 05, 06, 10, 11, 16, 17, 18, 20, 21 (waited for a live
  confirmation). Fire numbers 07, 13, 15, 19 have no session on the account.
- **Background runs, state unknown:** fire sessions 03, 04, 08, 09, 12, 14, 22 launched
  `setup + run` under `setsid nohup` with output to `/tmp/sim.log` and then went idle; the log
  and any OUTDIR live only in those containers.

The idle containers keep their files until the platform reclaims them for inactivity, so the
stranded raw files are releasable now but not indefinitely. See `RELEASE_STRANDED_RESULTS.md`.
