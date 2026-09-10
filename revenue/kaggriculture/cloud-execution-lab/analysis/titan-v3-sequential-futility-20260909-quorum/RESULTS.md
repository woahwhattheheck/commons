# QUORUM sequential-futility receipt

Operation: `titan-v3-fail-closed-sequential-futility-20260909-01`

## Frozen source boundary

- Repository: `woahwhattheheck/commons`
- Fresh-main base selected for publication: `690718ceca39095fd2ef2cea14fbadd4e9f0356d`
- Canonical paired-gate dependency blobs at that base:
  - `gate_common.py`: `7ed96f3147b437ef1e2c7868e752f625035f2c2f`
  - `contract.py`: `b0891bdb07d7e49749226bb86d4779d09e6b7155`
  - `gate.py`: `bbf68f6024937e24499b7e8ed45aa7cb1a6f05af`
  - `panel_load.py`: `b01607d68d5337603b9c415aa0ba9a1fd17e6fa3`
  - `metrics.py`: `288f35aa15b137c9bea67df5d3492abae1ce92f8`

The path-scoped workflow checks out the PR head and imports these adjacent
canonical modules from that checkout. Hosted CI is therefore authoritative for
the exact branch dependency closure.

## Local executable receipt

Environment: CPython `3.13.5`, `PYTHONDONTWRITEBYTECODE=1`,
`PYTHONHASHSEED=0`.

```text
Ran 32 tests in 0.559s
OK
```

The suite includes a deterministic bounded-soundness oracle:

- 250 independently sampled frozen promotion policies;
- a two-seat panel with terminal scores restricted to `{0, 1, 2, 3}`;
- every legal completion exhaustively enumerated whenever the partial gate
  returns `FUTILE`;
- every completion evaluated by the canonical full-panel
  `metrics.analyze()` + `evaluate_policy()` path;
- false `FUTILE` verdicts observed: **0**.

A source-replacement adversary is also covered: replacing the original panel
path after acquisition cannot change the parsed private snapshot or its report
hash.

## Synthetic interface receipt

Command:

```bash
python3 futility.py \
  --contract example/CONTRACT.json \
  --evidence example/PROVENANCE.json \
  --baseline example/canonical.GAMES.jsonl \
  --candidate example/challenger.partial.GAMES.jsonl \
  --report /tmp/quorum-futility.json \
  --quiet
```

Observed:

```json
{
  "candidate_cells": 3,
  "exit_code": 3,
  "optimistic_final": 0.625,
  "reason": "positive_cell_fraction",
  "remaining_candidate_cells": 5,
  "verdict": "FUTILE"
}
```

The frozen contract requires `0.75` positive cells. Five unrun cells cannot
raise three observed non-positive cells above `5 / 8 = 0.625`, so cancellation
is irreversible without relying on a score estimate.

## Published-file SHA-256 before GitHub commit

```text
65fbceb8b8ae46c83c531cc981a2ba232fc7be0ea2ed7bd98d0e2fbbf1113c2a  .github/workflows/titan-v3-sequential-futility-quorum.yml
36cd6a923fc9a2bba32cba43f3d3d014a6b0bce75655fd17ca8d30d0a0d2f73c  futility.py
e0a1493b8a17697cd1ccffdcabecdef69a06169512138db3539fd1cf011fa074  test_futility.py
77559932df7c4a7c21e824a2eace1f04270d3f735a2e1b3985c3e194af3bd3e7  README.md
8f0a3965bfc91be77332cce955ab1627decec463a1504e903576118868ae28c1  LICENSE-NOTE.md
3eaf34be0e9a579ec0eb6cc3568630423fc6e092cced3bc613b6c3b3c353ec04  example/CONTRACT.json
10fae815ca5cf1e071f460080fa0dd08ce926bbecd9d906aced114d2838c913f  example/PROVENANCE.json
162b9d6861f098b0fdc284ad6253fda8b86e296b240ea569c96e68248956aba8  example/canonical.GAMES.jsonl
0e0a1cba5fef0267486f0228243da815a2bb35f27b3fa583d585c9dea212281b  example/challenger.partial.GAMES.jsonl
23fadb260be9a71216980f35f09bab8ab180e53717209461689f69b0d90988bf  example/FUTILITY.json
```

## Scope and non-claims

This publication adds one analysis package, one path-scoped workflow, and
synthetic evidence only. It changes no gameplay, runtime, config, archive,
release pointer, provider state, or Kaggle submission. It makes no Titan score,
leaderboard, or first-place claim. Its concrete value is evaluator throughput:
a scheduler can reclaim remaining official-engine work only after an exact
partial snapshot proves that the frozen promotion contract cannot be rescued.
A partial panel can never produce `PROMOTE`.
