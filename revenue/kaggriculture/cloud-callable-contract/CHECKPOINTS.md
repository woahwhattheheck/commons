# Per-game executor checkpoints

`cloud-model-lab/execute_arm.py` now atomically saves each returned game row
before starting the next game. This fixes the previous end-of-panel-only write:
an interruption during a later attempt could otherwise lose all earlier rows.
The existing CLI and `--out` option are unchanged. Use a distinct output path
for each separately authorized run; this change does not resume, skip or replay
any game automatically, and cannot recover rows lost by an older invocation.

## Consumer contract

The original `candidate`, `control` and ordered `rows` fields remain intact,
including failure records, source labels, path annotations and TANDEM timing.
The additional `progress` object contains:

- `games_recorded`: returned rows saved, including failed attempts.
- `expected_games`: candidate plus control for every requested seed/seat/opponent.
- `failed_games`: saved rows whose original `error` is not null.
- `attempts_complete`: the loop and postprocessing finished with the expected
  row count. This is not an assertion that games succeeded or a policy improved.

The control row is saved before the candidate starts; the candidate row is
saved before optional path comparison. A further write retains its path
annotation. Final completion is marked only after the loop. Filesystem and
serialization errors propagate rather than silently continuing without a
checkpoint. Same-directory temporary files, flush/fsync and atomic replacement
keep the previous complete JSON intact if a write fails. A hard process exit
can leave a temporary file, but does not partially overwrite the last snapshot.
This protects completed rows while the filesystem survives, not against VM
deletion or every power-loss scenario. An unfinished in-flight game is not saved.

Writes run between games, outside the existing action and per-game timers.
They add filesystem I/O to total panel time; no throughput improvement is claimed.
`load_callable`, `normalise`, `game` and `wtl` are AST-identical to the accepted
source. CALLABLE's one-invocation repair and TANDEM's observer remain unchanged.
No policy, opponent, deadline, game order, seed allocation or running process is
modified by this delivery.

## Reproduction and measured scope

From the repository root:

```sh
python -B revenue/kaggriculture/cloud-callable-contract/test_execute_arm_checkpoint.py
```

All 15 focused methods pass on the delivered executor. Six interruption cases
fail as assertions, with no execution errors, on original executor Git blob
`224d3995f56dadc6762ebc2f35de6ea06ddee782` at
`ac3aca20247b016d26219708b51ef420fed9b987`. Set `TITAN_EXECUTOR_PATH` to an exact
old checkout's executor and select the first five interruption methods plus
`CheckpointContract.test_real_process_exit_retains_completed_control` to repeat
that before/after comparison. The validation JSON retains the exact method
names, original logs and source hashes.

The tests compile actual executor functions unchanged and replace only game
production with synthetic rows. They execute real file writes, fsync, atomic
replacement and an independent subprocess that calls `os._exit(23)` when the
candidate begins. The original leaves no output; the correction retains the
completed control. Failure injection also covers serialization, replacement,
fsync, path postprocessing, KeyboardInterrupt and SystemExit. No game engine,
policy evaluation, new seed, hosted workflow or previous panel rerun is included.
See `CHECKPOINT-VALIDATION.json` for full local results and identities.

Original executor and experiment work remain Claude's; invocation and timing
changes remain CALLABLE/TANDEM's. ASTRA-LANDING adds only checkpoint persistence
and its focused tests. Consumer: the next ordinary invocation of the existing
executor, not a restart of an active experiment.

The validation record's two `log` fields retain complete original output as
gzip-compressed base64. Decode with `gzip.decompress(base64.b64decode(value))`
and compare the decoded bytes to the accompanying `log_sha256`.
