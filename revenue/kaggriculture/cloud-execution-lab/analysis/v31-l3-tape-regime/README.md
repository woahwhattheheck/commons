# V3.1 L3 public tape-regime audit

Evidence tooling for the live L3 question only. This directory does **not** change TITAN defaults, package inputs, runtime gameplay, evaluator semantics, or Kaggle artifact bytes.

## Why this exists

The 41-live-game harm check for submission `56159263` found that late-sale suppression (L3) is opponent-regime dependent:

- overall: L3 changed margin by **-210.1/game**;
- 27/41 opponents classified as Shop-Router/tape-heavy: **-374.1/game** and worse in 24/27;
- 14/41 off-tape opponents: **+106.2/game** and better in 11/14.

That post-game split used `hands agreement >= 400/719 with best tape`. The useful policy question is narrower: can a comparable label be determined from information available *during the game*, before L3 first matters at step 648?

## Public-state theorem

The official interpreter exposes both farms publicly while each player's `private` payload is separate. Rival farmer/hand coordinates and unlocked quadrants are therefore public observations. Unit actions execute before the market. For an already-existing hand, whether a NORTH/SOUTH/EAST/WEST command changes its coordinate depends only on its previous public coordinate, board bounds, and public unlocked quadrants.

`l3_tape_regime.py` scores observed rival **hand-position transitions** against each of the 13 checked-in Shop-Router tapes over action steps 144..647. That gives up to 504 observations before the first L3 decision. It deliberately excludes:

- transitions where hand count changes, because successful HIRE can depend on market execution and hidden inventory;
- zero-hand transitions, because they contain no route information;
- malformed or skipped observations, which fail the entire game closed.

It never reads rival private inventory, shed, actions, market orders, replay labels, outcome, or future observations.

## Important non-equivalence

The live harm packet's `400/719` statistic and this online transition score are **not yet proven equivalent**. The scorer reports the same numeric reference ratio (`400/719`) only as a provisional comparison and always emits:

```json
"gate_ready": false
```

No runtime policy should use `PROVISIONAL_TAPE_LIKE` / `PROVISIONAL_OFF_TAPE` until the exact 41-game replay packet is run through this scorer.

## Required calibration before any L3 conditioner

For all 41 live games, record:

1. original harm label (tape-heavy vs off-tape);
2. this scorer's best tape, matches, comparisons, ratio at observation step 648;
3. confusion matrix against the original labels;
4. earliest step at which the eventual label would remain stable through 648;
5. per-group L3 delta-M using the same pinned-purchase replay protocol.

A production experiment may proceed only if the online score separates the groups without false `OFF_TAPE` classifications on the known tape-heavy games. Ambiguous or insufficient evidence must leave L3 **OFF**. The classifier must not flap once L3 becomes eligible.

## Run

Focused standard-library tests:

```bash
python -m unittest -v revenue/kaggriculture/cloud-execution-lab/analysis/v31-l3-tape-regime/test_l3_tape_regime.py
```

Score a JSON observation stream (`[...]` or `{ "observations": [...] }`):

```bash
python revenue/kaggriculture/cloud-execution-lab/analysis/v31-l3-tape-regime/l3_tape_regime.py observations.json
```

The tool loads the exact checked-in `candidates/v3/overlay/r01_tapes.py` tape bank and asserts its shape in the focused test suite.
