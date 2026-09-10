# TITAN V3 own-value promotion closure — SOL-PRO

## Disposition inherited from PR #12040

PR #12040 attempt 1 is terminal **screening evidence**, not promotion-grade
causal evidence. Its exact bank entered the official-interpreter stage in run
`34524185925`; all eight seeds are therefore spent regardless of the eventual
economic result, infrastructure conclusion, or timeout:

```text
1201189346,2053792019,684357706,572159600,
1619590821,1748784700,2100322278,1851971276
```

This successor does not amend that head, rerun that bank, select from its
result, or launch any replacement games. `SEED-RUN-LEDGER.json` records the
spend once and marks reuse forbidden.

The historical ledger policy digest is SHA-256 over canonical JSON binding exact
head `b1962a216fafd1c654fb96b2a4baa5fb81e2f1c0`, action-admission Git blob
`6a1ab9eeeb01fe6937bc0e56d540142f700172a6`, and workflow Git blob
`52b69ccad857fafea7a16c3c795d325021032f7c`; it is not a free label.

## Purpose

The own-value factor has a real score-facing development signal, but future
confirmation must close four independent evidence defects before the factor
can enter a one-tree integration decision:

1. a prose “one-shot” promise does not prevent manual dispatch, attempt 2, or
   reuse of the same bank;
2. one whole-game tested-action hash does not prove action → world → terminal
   causality;
3. hashing an entry shim such as `from scheduler import agent` does not bind
   the executable sibling package; and
4. opponent/seat rows sharing one environment seed are not independent units,
   while global means can hide a systematic bad-seed or lower-tail regression.

The verifier is split into reviewable standard-library layers: core validation,
immutable seed/run custody, executable closure manifests, native trajectory
causality, committed economic policy, and seed-clustered assessment. A small
`promotion_closure.py` facade exposes the composed contract. The test support and
three focused suites keep each predecessor surface independently reviewable.
Together they govern only a future fresh-label/fresh-seed panel. It performs no game execution and grants no
promotion authority.

## 1. Immutable seed/run custody

A game-spend receipt is accepted only when all of the following are literal:

- event is `pull_request`, never `workflow_dispatch`;
- `GITHUB_RUN_ATTEMPT == 1`;
- the checked-out `git rev-parse HEAD` equals the precommitted 40-hex head;
- operation, hypothesis, policy digest, run ID, source PR, and complete seed
  list are retained;
- all seeds are distinct and disjoint from every prior ledger entry;
- seed reuse is permanently forbidden.

`validate_append_only()` requires every prior ledger entry to remain bytewise
identical and permits exactly one appended spend. A future game workflow must
call `validate_run_environment()` **before** installing dependencies or
starting the first interpreter process, and must create the spend receipt
before revealing any economic result.

## 2. Dependency-closed executable roots

`build_closure_manifest()` recursively binds every regular file under a
control, candidate, or opponent execution root. It rejects symlinks and special
files, records byte count, SHA-256, and Git-blob SHA-1 for every member, binds
the declared entry, and binds resolved module origins to members in the same
root.

This prevents identical wrappers from laundering different executable
packages. The predecessor contract constructs two roots with byte-identical
`candidate.py` wrappers and different `scheduler.py` siblings; their closure
hashes must differ.

A future panel must retain separate closure-manifest hashes for control,
candidate, and every named opponent. Entry-file fingerprints alone are
insufficient.

## 3. Native first-divergence custody

Every arm/cell must retain exactly 719 step receipts. Each step binds:

```text
step index
preworld SHA-256
candidate observation SHA-256
tested-seat returned action SHA-256
rival returned action SHA-256
post-interpreter world SHA-256
post-interpreter bank SHA-256
```

For a changed cell, the verifier finds the first tested-action divergence and
requires:

- every earlier step is identical across control and candidate;
- preworld and tested observation are identical at the divergence;
- the simultaneous rival action is identical;
- the tested returned action differs; and
- the post-interpreter world differs immediately.

A no-op first action, prior world drift, prior observation drift, or simultaneous
rival-action drift is rejected as confounded. Later trajectory divergence is
then downstream of a witnessed realized action branch.

This is native paired-trajectory custody. It does not replace a separate
one-action intervention/ablation proof.

## 4. Score, trace, and replay closure

The complete trajectory digest is recomputed from the retained 719-step ledger
and terminal own/rival cash. Therefore:

- a detached trace hash is rejected;
- `NO_ACTION_CHANGE` cannot coexist with changed actions or economics;
- any terminal score change requires a changed complete trace;
- any terminal score change requires a realized first tested-action divergence;
- control and candidate primary invocations must be distinct; and
- every score-active control and candidate cell requires an independent replay
  with a distinct invocation ID, identical full trace digest, and identical
  terminal own/rival cash.

A replay of only the first scheduled cell is not sufficient.

## 5. Seed clusters and explicit tails

A future policy is a separate strict JSON object. Its canonical SHA-256 is
bound into the run receipt and panel before games begin, so thresholds cannot
be tuned after seeing the bank.

The policy must explicitly declare:

- global mean own-cash and margin floors;
- opponent × candidate-seat mean own-cash and margin floors;
- absolute minimum cell own-cash and margin floors;
- a lower quantile and own-cash/margin floors at that quantile;
- minimum per-seed mean own-cash and margin floors;
- minimum positive seed clusters and maximum negative seed clusters;
- maximum exact one-sided seed-cluster sign tail; and
- whether new losses, lost wins, and all outcome regressions are forbidden.

The verifier aggregates each environment seed across opponents and mirrored
seats before computing clustered support. With zero negative clusters, five
positive seed clusters produce exact one-sided sign tail `1/32`; mirrored
opponent/seat cells are never counted as independent sign trials.

No default economic floor is hidden in code. The one-tree owner must commit the
policy before the future run, and the run receipt must bind its canonical
digest.

## Verdict boundary

The strongest output is `PROMOTION_CANDIDATE`, accompanied by
`promotion_authority=false`. It means only that one fresh native paired panel
passed its precommitted custody and economic policy. Integration still requires
the one-tree owner, current-package composition, and any separately owned
causal/intervention or release gates.

A failed check returns `HOLD`. A red check is evidence and must not be weakened
or rerun on the same bank.

## Validation

The exact source ships with 26 predecessor contracts covering:

- attempt 2, manual dispatch, seed reuse, and mutation of prior ledger entries;
- identical entry wrappers with different executable siblings;
- closure tampering and symlink escape;
- score-active trace identity and `NO_ACTION_CHANGE` laundering;
- no-op first divergence, rival-action confounding, and prior-world confounding;
- absent or mismatched deterministic replays;
- incomplete both-seat grids and boolean identity fields;
- one systematically bad environment seed;
- absolute and lower-quantile tail failures;
- outcome regression hidden under positive global own cash;
- post-result policy changes; and
- duplicate/nonfinite strict JSON.

The included workflow is preflight only. It executes compile, all contracts,
ledger validation, exact-parent/path custody, clean-tree checks, and artifact
hashing. It has no `workflow_dispatch`, installs no game dependency, and
launches zero official-interpreter games.

## Boundary

No runtime policy, canonical config, selected archive, archive/source pointer,
provider state, Kaggle state, leaderboard state, submission, merge, promotion,
or release state is changed by this lane.
