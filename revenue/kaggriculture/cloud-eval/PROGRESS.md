# Interrupted CLI panels: retained game records

The existing `evaluate.py` command now writes an atomic progress snapshot after
each recorded game. No new runner or automatic resume path is introduced.

```sh
cd revenue/kaggriculture/cloud-eval
python -B evaluate.py --engine-dir /tmp/kag-engine \
  --candidate /cloud/candidate.py --opponent rival=/cloud/rival.py \
  --seeds 17,19 --output /cloud/my-panel.json
```

`/cloud/my-panel.json.progress.json` records progress. `/cloud/my-panel.json`
remains the final report and is replaced only when the invocation has processed
its complete panel and optional first-game recheck. An older final report at
that path remains unchanged if the new run is interrupted. Use unique output
paths for independent panels; a new invocation replaces that path's prior
progress sidecar, not a historical archive.

## Interpretation

The sidecar carries the original report fields, source fingerprints, recorded
rows and aggregate statistics, plus `progress`:

- `state`: `running`, `interrupted`, `error`, or `complete`.
- `phase`: `games`, `recheck`, or `finalize`.
- `planned_games` and `recorded_games`: requested ordinary cells versus returned
  rows. A returned failure is still a recorded row, not a successful game.
- `active_game`: the current opponent/seed/seat when a caught stop occurs;
  otherwise null at a saved game boundary.
- `recheck_requested`: whether the optional first-game replay was requested.
  Completed replay evidence remains in the original `reproducibility` field.
- `error_type`: exception class only when recording a caught interruption/error.

`complete` describes traversal of the invocation, not success of every game.
Existing exit behavior is preserved: a recorded game failure or replay mismatch
returns 1, while ordinary competitive losses alone return 0. A caught Ctrl-C
returns 130 and saves `interrupted`. Unexpected exceptions save `error` when
possible, then propagate unchanged. Recheck execution never adds another row to
the win/tie/loss aggregate.

SIGKILL, default SIGTERM, or host termination cannot run a final handler. The last
snapshot remains `running`, even if its record count equals the planned count
and an optional recheck/finalization was still pending. Never infer completion
from row count alone. There is no fabricated row, score, failure outcome, or
replay result for a call that did not return.

## Recovery and limits

Read or copy the sidecar before starting another invocation with the same output
path. Its exact recorded cells can be reconciled with existing lane-owned
journals. This change does not automatically resume, retry, merge studies,
reassign seeds, or turn previously consumed seeds into fresh validation.

All writes use a temporary file in the destination directory, explicit UTF-8,
flush/fsync, then `os.replace`. Serialization, write, sync, or replacement failure
keeps the previous destination snapshot; the temporary file is cleaned when the
process can execute cleanup. This is interruption-resistant file replacement,
not power-loss certification, multi-writer coordination, a remote backup, or a
promise that a hard kill cannot leave an unused temporary file. It does not
preserve an in-flight action or game. The accumulating snapshot is rewritten
once per returned game, not on each agent action; very large panels should
retain their existing specialized journals. Input fingerprints are sampled
before game execution and do not freeze arbitrary imported dependencies.

Neither `play`, `Actor`, worker IPC, official engine/scoring, source pins nor any
candidate strategy is changed. Direct users of `play()` keep their current
caller-owned persistence. No Kaggle or notebook write is involved.

## Focused verification

```sh
python -B -m unittest -v test_progress
```

22 tests passed on CPython 3.13.5 / Linux. Coverage includes actual replacement
and fsync ordering, partial-write/sync/replace/serialization faults, preserving
older final reports, pre-first-game and later interruptions, replay accounting,
failed-game/loss semantics, original opponent/seed/seat order, and real SIGINT
and SIGKILL subprocesses. Boundary rows are explicitly fixtures; these tests do
not execute competitive games or claim official-engine/hosted validation.

The two real-process cases both fail on baseline blob
`6bcde5b7dc1abc33eb3cd7ec42833affc2d28b53`: a printed completed fixture row has no
progress file after interruption. The repaired CLI retains that row and leaves
the older final report byte-exact. A separate caught-Ctrl-C reproduction records
the same difference. Fifteen existing function/class AST spans remain identical.
Exact hashes and execution details are in `progress-evidence.json`; full raw logs
are retained in the associated continuation package.

Original evaluator: ASTRA-WORK / TokenJunkieLabs / Bryce Muhlnickel. Final-worker
resource work from PR9871 and its PR9879 documentation remain intact. This
continuation is ASTRA-COORD, operation
`astra-coord-evaluator-progress-20260907-01`, coordinated in the existing Slack
thread `1788806580.945539` (claim `1788832638.147939`). Existing directory license
and upstream notices remain unchanged.
