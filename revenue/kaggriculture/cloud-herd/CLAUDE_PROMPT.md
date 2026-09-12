# Ready-to-send Claude prompt

You are testing and simulating Kaggriculture for Bryce / TokenJunkieLabs.
Root / Sanskrit Juggernaut coordinates this purchasing-lane handoff. LARK owns
the combined `claude-handoff/` manifest. Bryce explicitly requested:
"Give all stuff to sanskrit juggernaut so it can prompt claude for testing and running simulations".

Read `revenue/kaggriculture/cloud-herd/README.md` and `SOURCE_MANIFEST.json` first.
Use the exact commit containing this handoff, and record that checkout SHA.
Work in an ephemeral cloud environment. Preserve Euler, ASTRA-WORK and Rowan's
existing work. Do not use the owner's disk, Cursor, new paid services or llama.cpp.

Your deliverable is actual test and simulation evidence, selected exact bytes
if warranted, and a concise result for Sanskrit Juggernaut in the existing
[Kaggriculture thread](https://tokenjunkielabs.slack.com/archives/C0BUY2GT8P9/p1788752325435209).
Do not stop at a research report. Preserve all losses and failures. Root/account
owns replacement of the successful Kaggle notebook submission 347872961; this
task does not register a team, fork a notebook or make a duplicate submission.

## 1. Consume the existing team work

- Euler: `20260907-offline-agent/main.py`, `incumbent_20260907.py`, `candidate.py`,
  `compare.py`, `test_agent.py`, `README.md` and `ECONOMICS.md`.
- ASTRA-WORK: `cloud-market/main.py`, `study.py`, `diagnostics.py`,
  `test_study.py`, `test_behavior.py`, `selection.json`, `README.md`, `ECONOMICS.md`.
- Independent driver: `cloud-eval/evaluate.py`, `opponents.py`, `test_evaluator.py`,
  `README.md`. Use its actual interpreter, private-observation isolation, seed
  handling, crash/timeout accounting and trace hashes; do not invent a substitute game.
- SORREL: `cloud-herd/variants.py`, `experiment.py` and this handoff. These new
  candidates are parsed/generated only, with no new test or simulation results.
- Rowan: check the current thread for the published exact ref for its announced
  `cloud-dispatch/` continuation. No Rowan unpublished source was available here.
  Keep harvesting/scheduling experiments separate from purchasing comparisons;
  do not silently combine policies or pool measurements from different bytes.
- Kestrel: root routed crop/scarcity/price work to `cloud-crop-economics/`; get
  its current exact source ref from LARK/the thread before any combined comparison.
- Strong public opponents: root has Kaito Fukami SparseShopHybrid v43 notebook
  version 344404785 and Igor Zharov MultiRoute version 343725556 in Claude's VM,
  reported Apache-2.0. Root will provide the exact public inputs and extraction
  details. Record their actual source hashes and dependencies before evaluating.

Accepted lean20 evidence is carried forward: 42 tests, 96 development games,
64 validation games, four replays and eight diagnostic-equivalence games;
15/16 wins vs each Euler28 and compact22. The full prior evidence is
[run 34087144544](https://github.com/woahwhattheheck/commons/actions/runs/34087144544)
and [artifact 10005701500](https://github.com/woahwhattheheck/commons/actions/runs/34087144544/artifacts/10005701500).
Do not re-label these as new Claude runs or retune on those reserved seeds.

## 2. Prepare public source and candidates

Use Linux Python 3.11+; standard library only. Preparation is the networked phase.
From the repository root, using a fresh absolute cloud results path:

```sh
python -B revenue/kaggriculture/cloud-herd/experiment.py prepare --root /tmp/kag-herd-claude
python -B revenue/kaggriculture/cloud-herd/experiment.py candidates --root /tmp/kag-herd-claude
```

Verify all source and candidate SHA-256 values in `SOURCE_MANIFEST.json`.
The exact lean20 source is pinned to
`5d9fe82d288ee2933b38e8db8871602e688410af`; the existing peer snapshot is
`c57fc2962d7a0da5109162f0b6a267967c3a616e`; the unmodified official engine is
`28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`. Engine preparation verifies three
upstream Git blob IDs. Never copy credentials or restricted competition data
into logs, Git, Slack or the source package.

## 3. Test the new implementation before simulations

Own new tests under `cloud-herd/`; repair any real defects there before running
the study, and record any changes and resulting candidate hashes. Relevant cases:

1. Control generation is byte-identical to lean20; changed base source is rejected.
2. All eight generated files compile, import and return valid agent actions.
   The selected standalone must use only the standard library and public/current
   observations, without hidden seeds, runtime network calls or live-source imports.
3. Purchasing transformations retain the complete `claims = set()` onward unit
   scheduler verbatim. Existing action bounds and inventory semantics still hold.
4. With no new purchasing options enabled, the helper gives the original animal
   choice on representative market states. Pending livestock must count from
   our shed and our per-worker inventories exactly once, never another farm's
   inaccessible inventory.
5. Test price saturation, no profitable animal, cheap/expensive feed, late season,
   acquisition-cost weighting, batch size, repeated shop names, eight-shop cap
   and supported configuration overrides. Expected future shops must use the
   published distribution and timing, without reading a seed or future state.
6. Validate replay determinism and no mutation of the input observations or
   shared policy across calls. Confirm all prepared upstream hashes before games.
7. Retain the existing journal contract: changes to source/runtime/settings/seeds
   cannot resume into the same results; failure rows remain failures, not wins.
8. Check additional-opponent labels and callable paths, preserve the exact set
   between phases, and reject a changed or omitted opponent before validation.

The existing evaluator's 25 tests can validate the execution environment:

```sh
KAG_EVAL_ENGINE_DIR=/tmp/kag-herd-claude/engine python -B revenue/kaggriculture/cloud-eval/test_evaluator.py
```

Add the new tests and their exact command/results to the final report. Original
baseline study repetitions are not new independent validation data.

## 4. Run the predeclared purchasing study offline

Network-disable the simulation container. Use the existing 1.6 CPU / 6.5 GiB
workflow configuration as the resource template. Record the runtime image ID.
Pass `KAG_RUNTIME_IMAGE` into the container so the journal captures it. Mount the
repository read-only, give only the results path writable storage, and keep the
same absolute paths for resumptions. The driver enforces a one-second per-RPC
limit and 120-second per-game deadline; it is not the hosted Kaggle overage bank.

```sh
python -B revenue/kaggriculture/cloud-herd/experiment.py development --root /tmp/kag-herd-claude
```

Eight candidates × three development seeds (1543,4787,9431) × two seats × two
opponents (frozen lean20, Euler28) = 96 games without the additional public agents.
Root requested the strong public opponents as well: pass both exact prepared files
to development, using `--opponent kaito=/absolute/path/to/kaito.py::agent` and
`--opponent igor=/absolute/path/to/igor.py::agent` (substitute the actual callable
names and paths from root). This makes 192 development games. Selection maximizes
the smallest mean margin across all declared opponents, then overall mean and name.
Do not guess or silently omit either public opponent. The unmodified
control can win. The driver writes `herd-selection.json` and `selected_herd_main.py`.
Freeze and report those hashes before viewing validation. If a functional repair
changes the study, restart development in a fresh result directory with a new
contract; do not mix earlier results or quietly change the selection rule.

```sh
python -B revenue/kaggriculture/cloud-herd/experiment.py validation --root /tmp/kag-herd-claude
```

Selected bytes only × eight reserved seeds
(10657,15467,27653,39019,56393,79139,110221,190027) × two seats × four opponents
(lean20, Euler28, frozen compact22, goose20) = 64 games plus four opponent replays
without additional agents. Repeat the identical `--opponent` flags for the two
public agents: 96 validation games plus six replays. Their exact hashes must
match development; otherwise the driver rejects the phase.
Do not adjust the policy after viewing validation. If no credible improvement
survives, keep lean20 as the current candidate and deliver the measured negative
results and reusable tests; do not promote an unproven variant.

## 5. Return a complete, usable result

Publish source, tests, all game journals/reports, selection, source/runtime hashes
and exact standalone candidate in a durable cloud artifact or the owned Commons
path. Preserve MIT OR CC-BY-4.0 owner-code licensing and upstream Apache-2.0 notices.
Return one table per opponent with completed games, failures, wins/ties/losses,
mean and worst margins, paired-seed interval, timings and peak RSS. Include exact
loss rows and replay equality. Separate own results from inherited team results.

Land compatible owned changes on current Commons main, read back exact bytes,
and send the main SHA, artifact/PR links and your recommendation to Sanskrit
Juggernaut through its established route and the original Kaggriculture thread.
Sanskrit Juggernaut should pass any warranted replacement candidate to the
existing account/root session. Game coins, Kaggle submission success, leaderboard
standing and prize payment are distinct outcomes.

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../../../titanmcp.html). Cite Latch Pad KEEP.
