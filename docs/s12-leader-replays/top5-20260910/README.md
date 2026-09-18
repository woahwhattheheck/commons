# TITAN V3 S12b — top-five leader schedule study

## Verdict

The twelve supplied leader-vs-leader replays do **not** support copying one opening tape or maximizing one scalar such as workers, plants, cash, or land timing. They expose a stronger and narrower V3 target:

> **A competitive policy binds every returned worker command to the workers that actually exist in the immediately preceding observation.**

Across 24 leader seats and 17,256 audited decisions, the corpus contains **zero** worker-action cardinality overages. This remains true even though SpaTaro has four market rows in which five requested HIREs are rejected in aggregate. Those partial HIREs are not followed by phantom lanes; the next action adapts to realized worker count.

The exact submitted TITAN witness, episode `107130860`, does the opposite. Bryce has 45 overage rows in two contiguous blocks (`26–48`, `123–144`), 45 unreachable hand commands, and 26 unreachable non-`PASS` commands. Apa has zero. The unreachable non-`PASS` operations include movement, `PICKUP`, `FEED`, `CARE`, `WATER`, `COLLECT_FERTILIZER`, and `PLACE` work.

That makes **observation-bound actor realization** the highest-priority integration gate. HIRE solvency and opening liquidity remain valuable, but they are supporting mechanisms; a robust policy must still rebind or remove a lane whenever execution creates fewer workers than the route expected.

## Corpus and custody

The source set contains:

- 12 supplied leader-vs-leader episodes, 24 seats, 720 observations per seat;
- one exact submitted baseline replay, episode `107130860`, Apa versus Bryce Muhlnickel;
- compressed and decoded byte counts plus SHA-256 for every replay in `SOURCE.json`;
- no raw replay payload in this directory.

The physical-action audit uses the correct replay orientation:

```text
action[k] was selected from observation[k - 1]
```

Using `observation[k]` would silently bless an extra lane created by the action itself and miss exactly the regression under study.

## Exact findings

### 1. Physical closure separates the leader corpus from submitted TITAN

| Metric | Supplied leader corpus | Apa, episode 107130860 | Bryce, episode 107130860 |
|---|---:|---:|---:|
| Decisions audited | 17,256 | 719 | 719 |
| Worker-cardinality overage rows | **0** | **0** | **45** |
| Unreachable worker commands | **0** | **0** | **45** |
| Unreachable non-`PASS` commands | **0** | **0** | **26** |
| Rejected HIREs observed | 5 | 0 | 1 |

The leader result is not “every HIRE must succeed.” It is “the next action must reflect what succeeded.” That distinction matters because a pure cash-hoarding rule can reduce score, while physical closure is a state-consistency requirement.

### 2. The submitted opening produces the same day-zero assets but destroys working capital

Apa and Bryce both finish day zero with the same observed productive bundle:

- five workers;
- nineteen newly placed plants: twelve MELON and seven WHEAT;
- four animals: two COW and two SHEEP;
- first and second land unlocks at the same steps (`151`, `266`).

The schedule differs sharply:

| Metric | Apa | Bryce |
|---|---:|---:|
| Cash after step 2 | **984** | **52** |
| Cash at end of day 0 | **42** | **6** |
| MELON seed inventory peak, day 0 | **2** | **12** |
| MELON seed inventory-time, day 0 | **12 unit-turns** | **125 unit-turns** |
| Four HIREs requested at step 25 | 4 | 4 |
| HIREs realized | **4** | **3** |
| Workers after step 25 | **4** | **3** |

The twelve-seed MELON prebuy therefore changes no day-zero plant output in the witness, but it converts liquidity into idle paid inventory early enough to miss a represented next-day worker. This supports the existing Capillary/JIT-seed lane, with a stricter contract: stage only when the early purchase threatens an exact represented commitment, preserve every plant, and close worker cardinality afterward.

### 3. There are three viable opening families, not one tape

| Observed family | Seats | Hands after step 1 | Hands after step 2 | Mean max hands, day 0 | Mean plants, day 0 | Mean animals, day 0 | Mean MELON peak / inventory-time | First land unlock |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Otter Vibe immediate worker/asset | 8 | 5 | 5 | 5.0 | 20.0 | 5.0 | 6 / 98 | 121 |
| SpaTaro two-step expansion | 5 | 4.4 | 6.0 | 6.2 | 15.8 | 3.8 | 7 / 68.8 | 151 |
| Himanshu/Terry/pensukesan turn-one market staging | 11 | 0 | 5 | 5.0 | 18.636 | 4.0 | 3 / 12 | 151 |

Every supplied leader seat reaches at least five workers on day zero. That is a useful feasibility floor, but it is not a monotone score rule: matched winners had more, equal, and fewer day-zero workers in `3 / 7 / 2` games. Winners had earlier, equal, and later first land unlocks in `6 / 4 / 2` games. A V3 `opening_script` must therefore be bounded and state-selected, not a hard-coded copy of the highest-scoring replay.

### 4. Market round trips are evidence, not a safe direct port

Himanshu Kumar, Terry Luo, and pensukesan repeatedly use a turn-one WHEAT buy/sell staging pattern before buying five workers on turn two. The pattern is highly reproducible, but its same-turn cash effect depends on common-market order interaction. This corpus does not prove an all-rival-action dominance theorem, so the report explicitly rejects a blind round-trip clone.

Likewise, raw terminal `SELL` quantities are requested actions and can exceed stock. They are not realized-sale receipts and must not be ranked as harvested value without interpreter-bound execution evidence.

## Ranked V3 handoff

The complete machine-readable specification is `candidate-key-specs.json`.

### Rank 1 — `p07_realized_actor_binding`

**Seam:** `main.py::agent`, after all policy/market transforms and before returned-action receipt/history commit.

**Activation:** `len(planned_action.hands) > len(previous_observation.farms[player].hands)`.

**Required behavior:** preserve all addressable lanes; atomically reassign missing-lane work only under an exact physical-equivalence proof; otherwise omit the unreachable suffix. Never invent funding or workers, never alter farmer/market rows, and fail closed across day, route, checkpoint, inventory, or spatial-precondition boundaries.

**Admission:** full-game cardinality closure, candidate-action activation, preservation of every reachable effect, and both-seat matched official panels with no negative opponent-by-seat own-cash stratum.

### Rank 2 — `opening_committed_liquidity`

**Seam:** route compilation immediately before frozen SELL materialization; the existing isolated carrier is `titan_capillary.py::CapillaryTitanAgent`.

**Activation:** an already-planned expensive seed unit is paid for before it is consumed, and that premature purchase makes a represented HIRE, land, or animal commitment unaffordable before the seed is needed.

**Required behavior:** move only the existing seed quantity to the latest safe pre-plant executable slots; preserve total quantity, actor bytes, route topology, plant completion, and inactive suffixes; never rely on rival receipts.

**Admission:** nonzero returned-action activation, exact plant feasibility, positive mean and nonnegative median own cash, no negative opponent-by-seat stratum, and no new worker-cardinality overage. Fixed-tape liquidity reconvergence is not sufficient.

### Rank 3 — `opening_state_bound_mode`

Use the three observed families only as bounded templates. Select from current public state and exact commitments, stop permanently on the first mismatch, and hand control back to incumbent TITAN without modifying post-opening behavior. Each mode requires its own both-seat panel. A frozen universal tape is not supported by this corpus.

### Rank 4 — `land_unlock_timing_probe`

Otter unlocks at step `121`; every other supplied leader policy and submitted TITAN first unlocks at `151`. Earlier unlock wins six of twelve matched games, ties four, and loses two. Keep this as a lower-priority one-factor screen.

## What this report rules out

- maximizing day-zero workers without regard to executable work;
- copying one leader’s entire opening tape;
- cloning the turn-one WHEAT round trip without an all-rival market proof;
- treating requested terminal SELL quantities as executed liquidation;
- declaring HIRE solvency alone sufficient while stale worker lanes survive.

## Included machine evidence

- `SOURCE.json` — exact replay custody, teams, rewards, seeds, sizes, and both hashes;
- `findings.json` — compact exact findings;
- `candidate-key-specs.json` — ranked one-tree handoff and rejection boundaries;
- `team-summary.csv` — per-team leader-corpus aggregates;
- `matched-winner-comparison.csv` — paired winner-minus-loser schedule differences.

A strict stdlib extractor, five predecessor-killing tests, and the full generated evidence pack were also built and reproduced byte-identically before publication. They are intentionally not required by this docs-only PR.

## Claim boundary

This is observational replay analysis and a concrete V3 handoff, not a score-uplift or promotion claim. No controller, runtime, route bank, feature default, canonical archive, pointer, provider, Kaggle submission, or spend surface is changed here. Existing implementation owners retain P07, Capillary, T03, T02, one-tree integration, panel, merge, and submission custody.
