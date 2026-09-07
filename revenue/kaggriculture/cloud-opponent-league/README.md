# T09: frozen cloud opponent league

A paired, process-isolated tournament for the existing Kaggriculture policies. This directory adds an evaluator harness and observation-only opponent perturbations; it does not change the official engine, original parent policies, frozen cap configuration, or carrot export. It does not submit to Kaggle or establish a competition result, bounty award, sponsor acceptance, or payment.

Coordination: [T09 thread](https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788805928334039), ASTRA-FLOW. Other task owners retain their scopes.

## Inputs and pinned sources

| Component | Revision |
| --- | --- |
| Frontier source, original file adapters, evaluator and loader | `woahwhattheheck/commons@8329e78768906dc6e75ca3712e1690adc1ab2148` |
| Cap model and plan overlay | `woahwhattheheck/commons@473e63d7151d4acdcdeeb76c784aaf4054c062e3` |
| Official Kaggriculture engine, schema and utilities | `Kaggle/kaggle-environments@28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c` |

The source pack from [run 34155104262](https://github.com/woahwhattheheck/commons/actions/runs/34155104262), artifact `10030683172`, was exported without executing policies. Artifact archives have limited retention. The branch's `T09 public source pack` workflow records the exact source paths and revisions needed to regenerate it. Do not silently substitute newer upstream files.

The preparer checks each declared source member's Git blob and SHA-256 before staging, invokes the existing archive verifier and original Apex compiler, and retains upstream license files. It requires a compatible Linux environment, Python 3.10 or newer and a C++17 compiler. Preparation and tournament execution do not download dependencies or use credentials. The original native offline guard remains in the parent adapters.

## Reproduce

Obtain and unpack the source artifact so `SOURCE_MANIFEST.json`, `frontier/`, `cap/`, and `engine/` share one directory. Start in this directory. Use new, absolute paths outside this checkout; an existing runtime or result directory is deliberately not overwritten.

```sh
python -B -m unittest -v test_league.py

python -B prepare_runtime.py \
  --source-pack /absolute/path/source-pack \
  --runtime /absolute/path/league-runtime

python -B league.py freeze \
  --runtime /absolute/path/league-runtime \
  --output /absolute/path/league-freeze.json

python -B league.py run \
  --runtime /absolute/path/league-runtime \
  --freeze /absolute/path/league-freeze.json \
  --panel development \
  --output /absolute/path/league-development

python -B league.py run \
  --runtime /absolute/path/league-runtime \
  --freeze /absolute/path/league-freeze.json \
  --panel evaluation \
  --output /absolute/path/league-evaluation
```

Do not change the policies, opponent rules or selection criteria after inspecting evaluation. Running these exact evaluation seeds again is a replication, not a fresh holdout.

The freeze hashes `league.py`, `variants.py` and all non-bytecode runtime files, including compiled adapters, dependency sources, assets and preparation provenance. It verifies those hashes before and after each panel. A modified, missing or added runtime file invalidates that freeze. The generated adapters contain absolute paths, and compiler output can vary by environment: a rebuild in a different location gets a different runtime digest. This is source-pinned reproduction, not a promise of portable byte-identical binaries.

## Tournament design

Each panel has two seeds, two candidate seats, five opponents and three candidate arms: 60 games, 20 per arm. Every game uses new actor subprocesses and temporary homes through the unchanged `cloud-eval` evaluator. Environment seeds initialize the game, not policy inputs. The pinned evaluator's policy RNG and timeout contracts remain unchanged.

Development seeds: `9790001`, `9790019`.

Evaluation seeds: `9790101`, `9790119`.

Arms are intact Arlene (`control`), cap, and carrot. Cap uses the existing plan overlay with `max_steps=14`, `deposit=True`, `one_way=True`, `last_day=29`, `min_value=0.0`. Carrot uses the unchanged frozen frontier export with a file adapter. The same seed/seat/opponent triple is paired across all three arms.

Opponents are intact Arlene, intact Apex, Arlene with sale cadence, Apex with crop-demand filtering, and Arlene with labor cadence. These are deterministic stress variants, not presumed stronger opponents:

* Sale cadence filters existing SELL orders outside each fourth observed hour, with final-day and near-full-shed release exceptions.
* Crop demand counts currently unlocked shops, including duplicates, and filters less-supported crop sales when known positive demand exists. It uses the same release exceptions. No future shop schedule is inspected.
* Labor cadence filters HIRE orders on odd observed hours and retains at most the first HIRE on even hours.

No variant invents an order, changes unit actions, accesses hidden state, or carries variant state between games. `opponent_changed_turns` records whether a perturbation actually changed returned actions. An inactive perturbation must not be presented as independent evidence of robustness.

## Results and interpretation

Each panel writes `results.json` after every game. `complete: false` is a partial or interrupted panel, even when individual games succeeded. `complete: true` establishes that the panel reached its final freeze check; also inspect `invalid_games`, which must be empty before economic ranking is meaningful. The CLI returns nonzero for a completed panel containing invalid games.

The summary distinguishes W/T/L, own terminal bank cash, own-minus-rival margin, paired cash and margin differences, worst paired differences, and outcome flips relative to the matching intact-Arlene control. It includes seed, seat and opponent strata. Ranking uses wins plus half a tie, then mean margin; an alphabetical final tiebreak is not a statistical distinction. Terminal bank snapshots preserve actual cash when tied reward scores are zeroed by the official engine.

Compare development and evaluation rankings without selecting new parameters on evaluation. Four environment seeds total, correlated opponents, deterministic policies, and potentially inactive perturbations do not establish broad generalization or statistical significance. A win can coexist with lower own cash; both must be reported. Invalid runs are not silently scored as economic losses.

A loss, invalid game or paired cash/margin regression produces a `loss-traces/` JSON file. Traces retain daily checkpoints and the final eight action turns, sorted chronologically. They are bounded diagnostics, not a complete action replay. They contain candidate-visible economic observations, candidate actions, and the rival's action after both actions were selected; the latter is replay evidence, never additional policy input. Per-actor resource statistics and the unchanged evaluator's full engine trace digest remain in each result row.

## Validation and provenance boundaries

The regression module covers market-only transformations, observation immutability, duplicate-shop demand, day/hour and full-shed exceptions, fresh actor statistics, exact pairing, separate cash and margin accounting, invalid/empty/nonfinite rejection, disjoint seed panels, immutable runtime inventories, tied-bank cash preservation, and trace ordering. These unit checks are distinct from complete 720-step games.

Earlier transport and runner attempts, including a failed source-pack export, an assets-path error, and an earlier diagnostic development run, are not the release evidence. A prematurely reported 21/21 test count was corrected in the T09 thread. The release runner added evaluator-contract regressions and used a new freeze rather than overwriting those attempts. No earlier diagnostic run should be pooled into a new evaluation result.

The release operation announced freeze `9bd9e4bd977d7c36de9cc2fd06d0859f7f8c7c3fa4871544732c9f294b717653`. A freeze identifier alone is not evidence that either panel finished. Consult the corresponding completed result files and final receipt before claiming measured outcomes. This README deliberately does not infer scores from a queued, started or partially recorded execution.
