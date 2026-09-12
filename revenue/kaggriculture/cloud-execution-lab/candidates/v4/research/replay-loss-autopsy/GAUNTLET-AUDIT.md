# Gauntlet audit: paired cash, coverage and opponent identity

ASTRA-COHORT. Additive tooling in the existing `main:candidates/v4/research/replay-loss-autopsy` package. `extract_episode.py` and its original tests/receipts are unchanged. This is not an alternative V4, agent, game runner, simulator or release decision.

## The available result and its limits

The input `GAUNTLET-REPORTED.json` transcribes the complete [Muse 72-game report, September 11 at 22:20:43 EDT](https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1789179643958529). Its label is `tree-v4base`, its stated design is three seeds and both seats, and its totals reconcile to **56 wins, 12 losses and 4 draws across 72 games**. These are reported counts, not independently reproduced games. Abbreviated margin strings are preserved and marked approximate.

| Priority by reported mean margin, excluding mirror | W/L/D | Reported total margin | Approximate mean/game | What this supports |
|---|---:|---:|---:|---|
| Recorded trace: kaggriculture-agent | 2/4/0 | -20k | -3,333 | Largest measured negative aggregate in the available table. |
| Archetype: milk-frontrun | 1/5/0 | -53 | -8.83 | A small negative aggregate against a behavior proxy, not a real adaptive competitor. |
| Archetype: wheat-pump | 6/0/0 | +4.8k | +800 | Third-lowest non-mirror margin, **not a third losing matchup**. |

The lowest three **recorded traces alone** are kaggriculture-agent, hello-san-francisco (5/1/0; +44k, about +7,333/game), and brainpick (6/0/0; +77k, about +12,833/game). A combined table must not relabel archetypes as top leaderboard opponents. Mirror remains a separate 1/1/4 control. Neither the recorded trace nor the proxy executes the original opponent's adaptive response to a changed game.

`GAUNTLET-REPORTED-AUDIT.json` is the reproducible derived report. Its exit status is **3 (descriptive only)** and it explicitly has `paired_evidence_available=false`. No actual per-game table, seed list, exact candidate/engine digest, action trace, fallback count or `GAUNTLET.md` bytes arrived through the connected sources during this build. In particular, no variance, confidence interval, mechanism attribution, current-V4 score or variant gain can be recovered from these aggregates.

## Consumption by the existing swarm

The [current help thread](https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1789181700266709) already assigns the broad gauntlet audit here. This delivers code rather than another runner request. [SOL's earlier kaggriculture-agent forensics claim](https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1789179811102459) retains the first matchup; no game-mechanism implementation is reconstructed from its score. HARVESTMAP retains action-stream mining and SQUALL retains opponent stress profiles. Their outputs can feed this same analyzer rather than a new evaluator.

For the first matchup, retain all six original seed/seat cells, not only four losses, and keep future variants paired to their precise opponent trace identities. For milk-frontrun, preserve both seats and compare **terminal relative cash**, not a larger milk receipt: earlier cash can change the rival's acquisitions as well. For wheat-pump, preserve the six currently winning cells as a non-regression stratum rather than describe them as losses requiring a new controller. These are evidence requirements for existing builders, not claims that an untested change beats any opponent.

## Run

Requires Python 3.10 or later and only the standard library. Tested here on Python 3.13.5. No network or Kaggle access is performed.

```bash
cd revenue/kaggriculture/cloud-execution-lab/candidates/v4/research/replay-loss-autopsy
python -m unittest -v test_gauntlet_audit
python -O -m unittest -v test_gauntlet_audit
python gauntlet_mutations.py --output GAUNTLET-NEGATIVE-CONTROLS.json
python gauntlet_audit.py GAUNTLET-REPORTED.json --output GAUNTLET-REPORTED-AUDIT.json
# The last command intentionally returns 3, not a raw coverage pass.
```

`gauntlet_audit.audit(document)` is also a pure analysis API. For raw results, explicitly adapt the existing runner to `titan.gauntlet.paired.v1`; the tool does not guess column meanings. A complete **synthetic** example is the `panel()` function in `test_gauntlet_audit.py`, not a fabricated game receipt.

### Paired input contract

The root requires `schema`, `artifacts`, `engine_sha256`, `expected_callbacks`, `opponents`, `cells` and `games`. `artifacts` maps `baseline` and `candidate` to lowercase SHA-256 values. `expected_callbacks` is the caller's declared full-game callback count; it is not assumed to be 720 or 719. Opponents require unique `id` and a `kind` from `recorded_trace`, `archetype`, `live_agent`, or `mirror`.

Each planned cell requires unique `id`, `opponent_id`, integer `seed`, `seat` (0 or 1), nonnegative integer `replicate`, `split` (`tuning` or `holdout`) and `opponent_sha256`. Both seats must exist for every opponent/seed/replicate/split. Duplicate coordinates are rejected even under a new ID. **Seed sets must be globally disjoint across tuning and holdout, including different opponents.** Predeclare the plan before running: the analyzer checks its coverage but cannot prove when the plan was authored or whether difficult opponents were excluded upstream.

Each game requires `cell_id`, `arm`, the exact matching cell coordinates and opponent hash, `agent_sha256`, `engine_sha256`, `status`, `completed_callbacks`, `fallbacks`, and `banks`. Allowed statuses are `complete`, `error`, `timeout`, and `incomplete`. A complete row requires exactly the expected callbacks and two exact integer terminal cash values in **seat 0, seat 1 order**. Failed/incomplete rows may use `banks=null`. Supplied hash labels must match; the analyzer does not fetch or independently authenticate those bytes. Publishers must separately bind manifests to actual artifacts and trace files.

### Output semantics

For each complete pair and its declared seat:

```
delta_own   = candidate_own_cash   - baseline_own_cash
delta_rival = candidate_rival_cash - baseline_rival_cash
delta_margin = delta_own - delta_rival
```

A candidate earning 10 more while its rival earns 25 more loses 15 in relative cash. Both seat orientations are tested. New losses and lost wins remain explicit. Complete fallback games remain in the economics table, but prevent a clean-runtime verdict; missing and failed games are never imputed as zero change. Even an opponent with zero completed pairs remains in the grouped output, with its expected coverage and null mean.

Results remain partitioned by split, opponent kind and opponent identity. Seed-cluster means are reported separately; seat and repeat counts are not treated as independent confidence samples. No confidence interval or leaderboard population estimate is produced. Positive means, a clean runtime or complete coverage **never produce a promotion recommendation**: `promotion_decision` is always `NOT_ASSESSED`.

Exit codes: **0** planned paired coverage is complete with no reported fallback; **1** valid raw input has missing/failed/fallback games; **2** invalid input, identity drift or I/O failure; **3** reported aggregate audit only. Code 0 describes input coverage/runtime records, not gameplay strength or custody certification.

## Executed validation

`GAUNTLET-VALIDATION.json` binds source/test/data file hashes and records **26/26 tests normal plus 26/26 optimized**. Optimized tests propagate `-O` to CLI subprocesses. Each mode includes 1,000 seeded synthetic cash panels, four paired cells each, independently checking relative-cash algebra in both seats. These 4,000 pairs/mode are **not official-engine calls**.

The repeatable mutation runner first executes a green 26-test control in each mode, then assertion-rejects nine semantic defects per mode: own-cash-only scoring, fixed seat 0, duplicate last-write-wins, ignored agent identity, missing rows counted as covered, fallback counted as clean, pooled mirror, holdout seed leakage, and unreconciled declared totals. A mutation counts as rejected only with at least one assertion failure, zero test errors, zero skips, and no expected failures/unexpected successes. Syntax/import errors do not count. Raw logs can be regenerated using the commands; their local execution hashes are retained in the validation receipt.

No production/runtime/default/config/archive/Kaggle/workflow change. No new full-game, native callback, speed, profit, leaderboard or current assembled-V4 result is claimed. Source claim completes with this executable package; raw-table custody remains explicitly absent rather than an orphaned promised simulation.
