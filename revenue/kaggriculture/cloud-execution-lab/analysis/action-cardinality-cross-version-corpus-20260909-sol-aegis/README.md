# TITAN cross-version action-cardinality corpus — SOL-AEGIS

This is the non-colliding evidence companion to the live TITAN action-cardinality
gate. Another carrier owns the generic gate/runtime lane; this package supplies
the missing cross-version corpus and an independent reproducer.

The invariant is exact:

```text
len(action[k]["hands"])
    <= len(observation[k - 1]["farms"][player]["hands"])
```

Kaggle replay row `k` stores the action chosen from row `k-1`'s observation.
Comparing to row `k`'s post-action observation is an orientation error; the test
suite includes both a mutant-killing growth case and a shrink case.

## Result

Four separately uploaded submitted-V1 loss replays were audited by transport
and decoded JSON identity:

| Episode | gzip SHA-256 | Exact excess blocks | Rows |
|---|---|---|---:|
| `107113451` | `e7c8fad30e3014db67bca3691d9947b22874275eeb57ba0f917625a47c29aad0` | 123–144 | 22 |
| `107130860` | `9337c7c734eff0804400f732d48c155dedb6d6f12b3afdefbc620f78fdfc686b` | 26–48; 123–144 | 45 |
| `107142511` | `a18879c53613cb90f75e6f31f8d60c9726c490fd4ec6c753d3e90e69a1555d68` | 123–144 | 22 |
| `107150217` | `29725fd6d06a5a6cf736427a9a64fc0b43b573d469cf47dec2d824a17d7b5f38` | 123–144 | 22 |

Aggregate: **5,752 decisions**, **111 unreachable hand rows**, maximum excess
one row per decision, all on Titan/Bryce seat 1. This corrects the provisional
“V2-only” characterization: the reachability defect is cross-version.

Every day-5 block has the same 22-opcode unreachable suffix. Canonical opcode
sequence SHA-256:

```text
a8db2e6b2e3e1a5206eabfac07da7dd1037ce0c2f47dc47dc191474fd00e6206
```

The early `107130860` block loses work-bearing commands: `PICKUP`, `FEED`, two
`CARE`s, `COLLECT_FERTILIZER`, `PLACE`, plus movement/PASS. Aggregate opcode
counts are sealed in `CORPUS.json`.

These facts prove submitted-action reachability loss in the identified bytes.
They do not prove a score delta, source causality, engine equivalence, candidate
strength, or release readiness.

## Files

- `CORPUS.json` — compact, canonical, self-bound source/block/opcode manifest.
- `verify_corpus.py` — strict manifest verifier and optional independent raw
  replay reproducer.
- `test_verify_corpus.py` — 10 adversarial and orientation tests.
- `run_tests.sh` — compile, test, and committed-manifest verification.

`CORPUS.json` self-hash:

```text
ef320c17e787f8e8e8821e61aefda118980e152fe0f69b6a37f58eba3fa597fc
```

The manifest records both gzip and decoded-JSON byte counts/SHA-256 values,
Slack file IDs, exact contiguous blocks, observable/submitted cardinalities,
and unreachable opcode sequences. `automatic_promotion` is fixed to `false`.

## Verify

```bash
cd revenue/kaggriculture/cloud-execution-lab/analysis/action-cardinality-cross-version-corpus-20260909-sol-aegis
./run_tests.sh
```

Expected final line:

```text
PASS mode=manifest sources=4 decisions=5752 unreachable_rows=111 corpus_sha256=ef320c17e787f8e8e8821e61aefda118980e152fe0f69b6a37f58eba3fa597fc
```

With the four gzip files present under their episode filenames:

```bash
python -B verify_corpus.py --replay-dir /path/to/replays
```

That mode independently:

1. checks gzip byte count/hash;
2. performs bounded decompression and checks decoded JSON count/hash;
3. rejects duplicate JSON keys, NaN/Infinity, malformed frames, seat/player
   disagreement, or malformed hand actions;
4. replays every seat using `action[k] <- observation[k-1]`;
5. requires the exact decisions and excess rows in `CORPUS.json`, with no extra
   or missing finding.

The corpus digest is an integrity binding, not a signature or custody root. The
Slack generation/outcome labels are external metadata; they are not inferred
from replay JSON.

## Scope

No controller, policy source, route planner, HIRE transform, engine, evaluator,
archive, CURRENT pointer, opponent, seed, provider, Kaggle submission, or spend
surface is modified. No score or automatic-promotion claim is made.
