# TITAN V4 terminal-fallback raw-slot completion

**Status: built and tested locally; NOT published to GitHub or posted to Slack.**
No merge, production update, feature-default change, branch, Actions run or Kaggle
submission was performed. This session exposed read-only GitHub and Slack tools.

Operation: `V4-TERMINAL-FALLBACK-RAW-SLOT-COMPLETION-20260911-01`.
The single intended custody destination is this directory on `main`, under the
existing `revenue/kaggriculture/cloud-execution-lab/candidates/v4` workspace.
This is not another V4 product or successor branch.

## Scope and findings

The current production-source `reference/titan-current/deadline_adapter.py` has
two terminal-fallback boundary/representation-order defects:

1. Its raw Python slice uses `int(maxMarketOrdersPerTurn)`, whereas the pinned
   interpreter uses `max(1, int(maxMarketOrdersPerTurn))`. A configured zero or
   negative value can therefore suppress a sale the engine will execute.
2. The shed can contain three animal types as well as nine saleable products.
   Animal SELL rows are invalid but consume raw market slots. With a reordered
   shed mapping, such rows can crowd valid product lots out of a ten-slot queue.

**This is not an observed ladder-strength gain.** The engine normally initializes
shed keys with products before animals, and the standard order limit is positive.
The reordered/default-limit and nonpositive-limit witnesses here are constructed
observations/configurations. Natural hosted activation and full-episode payoff
have not been measured.

## Repair and composition invariant

`deadline_adapter.py` is the complete, exact tested postimage. Only the bottom of
`terminal_liquidation_fallback` changes. Timer code, deadline ownership, legal PASS,
DROP actor ordering, shared-capacity accounting and entrypoint behavior are not
changed.

The repair matches the engine's minimum-one clamp. For animal rows inside the
executable prefix, it fills only otherwise-inert slots from product SELL lots
outside that prefix. Every already-executable valid SELL keeps its values and
**the same raw row index**. It does not filter/compact the queue, which would move
those orders relative to the rival's lockstep market rows. Extra animal rows with
no omitted product to recover deliberately remain unchanged.

Preserving row positions is not a theorem of economic dominance against every
opponent. Added sales can affect a rival's later market behavior. The randomized
paired test deliberately uses fixed SELL-only rivals and makes no broader claim.

## Exact provenance

- Production source: `664aa4f8a21368c388dfa6714406519b6535ef7f`.
- Source revalidated on main commit: `c0ec870bf6019cc9270a9f1cfb46c3f2676fb258`.
- Repaired postimage: `8f36fbe5d05fb71731ef4b799a664189a6dae153`.
- Postimage SHA256: `b52ec11648b235bccace7b298db85eb4f82428de4191c37876a395b1733772dc`.
- Official engine: `3c202c7ee921da239356789e266b694635103fc4`.
- Offline source/engine artifact: GitHub Actions artifact `10285621024`, checkout
  `8250aec877974e9a1feba2b8e33fcd51000857d4`.

The artifact's deadline adapter exactly matches the current source above. Its
other runtime files are older; tests using those files are separately labeled
compatibility evidence, not a validation of the whole current V4 assembly.
See `SOURCE.json`, `receipt-*.json` and `MANIFEST.json` for complete byte identities.

## Executed evidence

Python 3.13.5: **25/25 focused tests normal + 25/25 optimized (`-O`)**.
Both modes execute the full pinned engine interpreter, not a substitute market
model. Each mode includes the same **704 constructed terminal-state cells**:
512 paired predecessor/candidate cells and 192 market-limit boundary cells.
This is 704 unique constructed cells repeated under the two interpreter modes,
not 1,408 independent games.

In the 512 paired fixed-SELL-rival cells, 198 margins strictly improved, 314
returned identical actions, and the minimum margin delta was zero. The test also
checks exact original valid-row positions, no observation mutation, both seats,
post-unit DROP sales, shared capacity, off-shed actor exclusion, hash guards and
unchanged AST outside the terminal function.

Constructed actual-engine examples, both seats:

| Fixture | Predecessor final cash | Repaired final cash |
| --- | ---: | ---: |
| One MILK, configured limit 0 | 0 | 160 |
| Reordered shed, animals first; WOOL/FERTILIZER overflow, limit 10 | 700 | 11,268 |

The 10,568 difference in the second fixture is **not** a measured per-game edge.

An isolated copy of the older materialized runtime also passed its existing
worker-deadline (6), entrypoint-clock (2) and module-recovery (3) tests:
**11/11 normal + 11/11 optimized**. Only its deadline adapter was replaced.

## Reproduce without changing production

Let `LAB` be the root of the materialized `seed-retry-runtime` from artifact
10285621024. It must contain the pinned original
`reference/titan-current/deadline_adapter.py` and the complete offline
`checks/reference/engine` and `checks/reference/evaluator` caches. Let `HERE` be
this repair directory. The test verifies engine file hashes before execution and
uses no network.

```sh
python "$HERE/test_terminal_fallback.py" --lab-root "$LAB" --receipt /tmp/normal.json
python -O "$HERE/test_terminal_fallback.py" --lab-root "$LAB" --receipt /tmp/optimized.json
python "$HERE/repair_terminal_fallback.py"   "$LAB/reference/titan-current/deadline_adapter.py"   --output /tmp/deadline_adapter_candidate.py
```

The output path must not exist. The transformer refuses to overwrite its input,
refuses a changed source blob, refuses a second application and verifies the
complete expected postimage; these guards do not rely on `assert`.

To reproduce compatibility, make a separate copy of `LAB`, replace only its
`reference/titan-current/deadline_adapter.py` with the shipped postimage, set
`PYTHONPATH` to that copy and its `checks` directory, and run:

```sh
python -m unittest -v test_worker_deadline.WorkerDeadline   test_entrypoint_clock.EntryClock test_module_recovery.ModuleRecovery
python -O -m unittest -v test_worker_deadline.WorkerDeadline   test_entrypoint_clock.EntryClock test_module_recovery.ModuleRecovery
```

## Integration disposition

The outer `titan-v4-terminal-fallback-custody.patch` adds this evidence directory
only. The inner `terminal_fallback.patch` is the narrow proposed production diff,
for review and independent current-assembly gates, not automatic promotion.

Refresh main and the source blob before consuming. An equivalent earlier repair
wins; do not overwrite concurrent work. Preserve these bytes under the one
canonical V4 workspace, revalidate the current full runtime before activation,
and leave unrelated gameplay/default/archives alone. The old r04 materializer is
not involved. `SLACK-HANDOFF.md` is prepared text and was **not sent**.
