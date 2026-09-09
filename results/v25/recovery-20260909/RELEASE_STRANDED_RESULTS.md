# Releasing the stranded raw files

The 14 completed shards (B, C, D, E, G, I, R, S, T, U, V, W, X, Y) and the 7 launched fire
sessions (03, 04, 08, 09, 12, 14, 22) still hold their `SUMMARY.json`, `GAMES.jsonl`,
`shard*.json` and/or `/tmp/sim.log` in their own idle containers. They are all still
SESSION_STATUS_IDLE (not archived), so a single message to each one releases the files.

## Option 1 — paste this into each session (desktop app / claude.ai/code → the session → type)

```
Push your v25 sim results to git now. Copy your run's SUMMARY.json, GAMES.jsonl, shard*.json and /tmp/sim.log (whichever exist) into results/v25/<SLUG>/ in the repo, add results/v25/<SLUG>/meta.txt with your session title and the exact run.sh arguments you used (seed start, count, outdir), then:
git checkout -b v25-results/<SLUG> && git add -f results/v25/<SLUG> && git commit -m "v25 sim results: <SLUG>" && git push -u origin v25-results/<SLUG>
If the sim is still running, wait for it to finish first. Do not start a new run. Reply with the SUMMARY.json contents.
```

Replace `<SLUG>` with `sim-shard-B`, `cloud-shard-R`, `fire-03`, etc. Each session pushes to
its own branch, so the pushes cannot collide. Afterwards any session can collect them with:

```
git fetch origin 'refs/heads/v25-results/*:refs/remotes/origin/v25-results/*'
```

## Option 2 — let a Claude session do the fan-out

A session on this account can bind a poke trigger to each shard (Claude Code Remote
`create_trigger` with `persistent_session_id`) and fire it with the message above. In the
recovery session that action was blocked by the auto-mode permission classifier; allowing it
(or running the recovery session in a mode that permits cross-session triggers) lets one session
release all 21 shards at once and assemble the zip.

## Sessions

| slug | session id | title |
|---|---|---|
| sim-shard-B | session_01BEfbCpCyHig6aaNjyPYzL3 | v25 sim shard B |
| sim-shard-C | session_01LfXjktpwoMpYMxsUc8FwHv | v25 sim shard C |
| sim-shard-D | session_01RYsCHSxeHXFTGz3NjS1yaY | v25 sim shard D |
| sim-shard-E | session_014udW9T2jABMkdZdiUdJByC | v25 sim shard E |
| sim-shard-G | session_018iKDkvLmKge59qdxQcnTZ1 | v25 sim shard G |
| sim-shard-I | session_01G4GKqQS5WwRd8fZUkM7J9S | v25 sim shard I |
| cloud-shard-R | session_01SuKtS3duDdQHGGMMErUWaC | v25 cloud shard R |
| cloud-shard-S | session_01AGrpymYoXngWJogUtbRuMW | v25 cloud shard S |
| cloud-shard-T | session_01BXymi7hbJPCpETEDbzDT5q | v25 cloud shard T |
| cloud-shard-U | session_01XEsEBcvRG1URcTYSbeDoUj | v25 cloud shard U |
| cloud-shard-V | session_011zPyQ7nerMp5De7UrMCfSH | v25 cloud shard V |
| cloud-shard-W | session_01MTCDSWG4xuabJe6rG4jb9c | v25 cloud shard W |
| cloud-shard-X | session_01GFvuU69nBiZzGxkBvYYoEw | v25 cloud shard X |
| cloud-shard-Y | session_01FhwgJDQUWQqLFghDLSA2EN | v25 cloud shard Y |
| fire-03 | session_01CfMi6YWv3gaiSD88YYQj98 | v25 fire 03 |
| fire-04 | session_01X2UdLRPcDWqKiN7tSKvp1R | v25 fire 04 |
| fire-08 | session_01QCHtTddVUMXk2u7dYJMkNz | v25 fire 08 |
| fire-09 | session_015MRCSd4Asn4Eoo3pkaRirj | v25 fire 09 |
| fire-12 | session_01BqogfYGhT8pcenaWKNvNWR | v25 fire 12 |
| fire-14 | session_01UrKAxwjCEbKVmCMDa34L9t | v25 fire 14 |
| fire-22 | session_01CbmrJZ16quGbkQ3BNMY239 | v25 fire 22 |

The parent session (session_01PJzDkwuT5UKKnAHNNjBTjX, "V2 simulations setup") also still
holds the raw Panel A / Panel B output in its container; the same message with slug
`parent-panels` releases it.
