# Kaggriculture independent tournament evaluator

KAG-EVAL adds a reusable evaluator alongside Euler's accepted agent, without
editing its source, policies, tests, or original evaluator. It uses the existing
`../20260907-offline-agent/evaluate.py:get_engine` loader and the **unmodified
[official interpreter](https://github.com/Kaggle/kaggle-environments/tree/28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c/kaggle_environments/envs/kaggriculture)**,
pinned to `28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`. All three upstream source
files must match their recorded Git blob IDs before offline execution.

## Run in ephemeral cloud storage

Python 3.11+ on Linux, standard library only. No Kaggle login, competition data,
model API, package installation or new paid service is needed. Source preparation
is a separate network-enabled step; evaluation itself never downloads missing files.
Do not create this build/cache on Bryce's machine.

```sh
cd revenue/kaggriculture/cloud-eval
python -B evaluate.py --prepare-engine /tmp/kag-engine
KAG_EVAL_ENGINE_DIR=/tmp/kag-engine python -B -m unittest -v test_evaluator test_final_usage
python -B evaluate.py --engine-dir /tmp/kag-engine \
  --seeds 2027,6607,104729 --recheck-first --output /tmp/tournament.json
```

The supplied GitHub Actions workflow performs preparation first, then runs tests
and games in `python:3.11-slim` with `--network none`, a read-only source mount,
1.6 CPU and 6.5 GiB memory limits, and ephemeral writable temporary storage.
The image ID, exact checkout commit, source hashes, tests and JSON results are
retained in its artifact. It does not create or submit a competition entry.

To evaluate another independent strategy, use a file exporting `agent(obs, cfg)`
or `agent(obs)`; another function can be selected with `::function`:

```sh
python -B evaluate.py --engine-dir /tmp/kag-engine \
  --candidate /cloud/path/candidate.py \
  --opponent rival=/cloud/path/rival.py::agent \
  --opponent starter=official_starter --output /tmp/comparison.json
```

Each supplied seed runs both player positions. The default suite is the official
starter, an independent four-tile wheat patrol, and a seeded random crop/walk
policy, plus Euler’s requested `compact_no_expansion` ablation (22 animals, no
land expansion, nine hands). The compact variant is explicitly an ablation,
not an independent policy; its imported agent dependency is also fingerprinted.
The other simple baselines are **not a claim of strong competition opposition**.
A successful first-game replay checks the score and full action/final-state hash;
its extra game is excluded from the aggregate to avoid double-counting.

## What is measured

Each game records terminal money scores, player positions, the seed, day-by-day
bank balances, action/final-state hash, elapsed time, and per-agent decision/RPC
latency, CPU time, peak resident memory and exit code. Resource values include
worker startup/import overhead. Available Linux process readings before cleanup
are supplemented by final `wait4` child usage where supported, so a timed-out or
abruptly exiting call need not lose its last resource measurements.
`resource_sample` and `final_resource_sample` identify the actual sources;
[final-usage notes](FINAL_USAGE.md) describe fallback behavior and measured limits.

Agents run in separate fresh persistent processes and working directories.
Each process receives only its own observation and a copied configuration. The
interpreter resolves and removes the world seed before either agent runs; the
separate agent RNG seed depends on candidate/opponent role, not the world seed
or player position. Standard `random` and `PYTHONHASHSEED` are seeded. An agent
using fresh OS entropy, unseeded `random.Random()`, a clock, or other libraries
is not thereby made deterministic; `--recheck-first` exposes a mismatch.

Startup errors, Python exceptions, abrupt exits, invalid actions, partial or
oversized protocol frames, and timeouts are explicit failures. A failed game has
`scores: null`; its money snapshot is diagnostic, **not a final score or win**.
Completed games alone contribute to win/tie/loss and mean-margin statistics.
The CLI exits nonzero for a failure or replay mismatch while retaining its JSON
report. Losing legitimately does not make the evaluator exit nonzero.

## Deliberate limits

This is an **explicit driver of Kaggle's interpreter, not the hosted Kaggle
runner**, leaderboard validation, a submission receipt or a prize result. The
default one-second deadline is a strict per-RPC development limit, including
serialization and transport. It does not emulate Kaggle's extra-time bank;
observations advertise zero remaining overage time. Startup has a separate
10-second limit. The 120-second game deadline is checked between interpreter
steps and bounds each agent RPC; the CI job also has a ten-minute hard limit.
`--episode-steps` supports short integration tests; benchmark defaults retain
720 recorded states (719 action rounds), following the upstream terminal rule.

The JSON IPC never deserializes agent-generated pickle. Agent print output is
discarded to avoid corrupting protocol messages. Process separation protects
normal game-state ownership but is **not a security sandbox for hostile code**;
run only trusted candidate modules inside the supplied isolated container.
Agents share that container's CPU/memory budget. Decision timings are
child-reported; parent-enforced RPC timing and OS resource readings are separate.
Only Python entry files are fingerprinted for arbitrary agents: separately pin
and record any dependencies that a third-party candidate imports.

## Tests and provenance

`test_evaluator.py` contains harness fault-injection tests and eight tests against
the actual official interpreter. Local runs without a source cache explicitly
skip those eight; CI supplies the verified cache and must run them. Live tests
cover terminal off-by-one behavior, score semantics, private observations,
hidden seeds, repeatability, different world seeds, crashes, timeouts, seats, and isolation of the compact policy overrides.
Fault-injection agents are test fixtures, not benchmark opponents or simulator
substitutes. No Euler results are reopened or overwritten.

`test_final_usage.py` adds eight real-worker resource and cleanup regressions.
For the focused resource checks alone, without preparing an engine or running
any games, use:

```sh
python -B -m unittest -v test_final_usage test_evaluator.ActorTests.test_timeout_resource_measurement
```

These cases cover unavailable procfs, final allocation/CPU usage, normal and
signal exit codes, unavailable/interrupted wait4, and repeated cleanup. The
[landed validation record](FINAL_USAGE.md#validation) distinguishes these checks
from the original interpreter tests and earlier tournament results. The manual
full-test command above includes both test modules; this documentation change
does not alter the GitHub Actions workflow or claim a new CI execution.

Work order: [KAG-EVAL coordination](https://tokenjunkielabs.slack.com/archives/C0BTB4SUCP9/p1788753053465569).
License for these new files: CC-BY 4.0. Attribution: TokenJunkieLabs / Bryce
Muhlnickel; implementation by ASTRA-WORK. Upstream Kaggle files retain their
own Apache-2.0 terms and are fetched rather than republished here.
