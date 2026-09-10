# First-divergence causal action splice

`causal_action_splice.py` answers a narrower and more useful question than a
source diff:

> When the candidate first returns a different action on the same public
> trajectory, does executing that one action improve the terminal result?

It is an offline diagnostic. It uses the pinned official interpreter and the
process-isolated `Actor` implementation in `evaluate.py`. It does not upload a
submission, call Kaggle, or require network access.

## Experiment

For each seed and focal seat, the evaluator runs:

1. **Baseline discovery.** Baseline controls the game. Candidate is a shadow
   process receiving the exact same focal observations until its first returned
   action differs. Only baseline actions reach the interpreter.
2. **Baseline replay.** Baseline is rerun without the shadow. Exact trace and
   scores must match discovery.
3. **Candidate native + replay.** Candidate controls two identical runs. Exact
   trace and scores must match.
4. **Candidate action on baseline.** Baseline remains the policy process, but
   the candidate shadow's action is executed at the discovered step. Baseline
   resumes on the resulting observations.
5. **Baseline action on candidate.** Candidate remains the policy process, but
   the baseline shadow's action is executed at the discovered step. Candidate
   resumes on the resulting observations.

Before an intervention, policy and shadow actions must match on every step. At
the target, the observation hash, prefix-trace hash, and both action bytes must
match discovery. A mismatch is `unstable`, not evidence.

The two causal margin estimates are:

- `candidate_action_on_baseline`: treatment run minus baseline;
- `candidate_action_on_candidate`: candidate native minus ablation.

A cell is `supported` when both are positive, `harmful` when both are negative,
`neutral` when both are zero, and `mixed` otherwise. `dormant` means no returned
action divergence appeared on the full baseline trajectory. These labels apply
only to the first changed output in that seed/seat/opponent cell. They do not
attribute an entire feature, transfer results to other opponents, or predict a
hosted leaderboard score.

## Run

From this directory:

```sh
python -B test_causal_action_splice.py

python -B causal_action_splice.py \
  --baseline ../../exports/historical/<baseline>.tar.gz \
  --candidate ../../exports/titan-current.tar.gz \
  --opponent official_starter \
  --seeds 2027,6607,104729 \
  --seats 0,1 \
  --output causal-action-splice.json
```

`--baseline` and `--candidate` each accept:

- a deterministic TITAN `.tar.gz`/`.tgz` archive containing root `main.py`;
- an extracted directory containing root `main.py`; or
- an evaluator entry specification such as `/path/main.py::agent`.

The default engine directory is `../engine`, whose source hashes are verified
by `evaluate.py`. Other evaluator limits can be changed with
`--action-timeout`, `--startup-timeout`, `--game-timeout`, and
`--episode-steps`.

## Receipt

The JSON report records:

- engine ref and SHA-256 hashes;
- archive, entrypoint, loader, evaluator and splice-evaluator hashes;
- seed, seat, day, within-day step, observation and prefix hashes;
- complete baseline and candidate actions plus structural differing paths;
- native, replay, treatment and ablation scores/traces;
- focal-score, opponent-score and margin effects;
- per-cell classification and aggregate mean effects.

Archive extraction accepts only bounded regular files and directories. Absolute
paths, traversal, links, devices, missing root `main.py`, oversized members and
oversized expanded archives are rejected.

The command exits nonzero for `failed` or `unstable` cells. `dormant`,
`supported`, `harmful`, `neutral`, and `mixed` are completed measurements and
therefore do not alter the exit status.
