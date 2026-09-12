# TITAN V3.1 H5 — terminal animal-capital ROI guard

Status: **default-OFF experiment / source carrier only**.

## Narrow theorem

The frozen V3.1 R04 route enters its final plan at step 648 and the standard 720-step episode's last action is step 718, leaving at most 70 action turns. The official animal timing used by the prior H5 research packet is GOOSE first yield after 4 days (96 turns), SHEEP after 6 days (144), and COW after 8 days (192). A newly purchased standard animal in this final-plan window therefore cannot reach first production before terminal under the pinned 24-turn day.

This successor deliberately does **not** implement a generic "spend less late" policy. It only blanks proven-dead `BUY_ANIMAL` rows, in place, and leaves worker commands plus every SELL/HIRE/BUY_LAND/BUY_PRODUCT/BUY_SEED row unchanged.

## Affordability hardening

Removing a purchase can make a later same-turn cash-consuming row affordable. That would turn a local capital-savings theorem into an uncontrolled policy rewrite. H5 therefore edits only the proven-dead animal-purchase suffix after the last other non-SELL/non-placeholder market row. Earlier dead animal buys remain untouched if a later HIRE, land/product/seed buy, unknown order, or other protected row could observe the saved cash.

## Fail-closed boundary

The experiment preserves the exact parent action when any of these are ambiguous:

- timing differs from the pinned `turnsPerDay=24`, `episodeSteps=720` contract;
- step is missing or not a literal non-bool integer;
- a known `BUY_ANIMAL` row has a malformed shape, animal, or quantity type;
- the market queue contains a structurally malformed non-empty row;
- all proven-dead buys precede a protected downstream spend.

`bool`, float, and numeric-string timing/quantity aliases are explicitly rejected rather than normalized with `int()`.

## Provenance

This is the narrowed successor to closed research PR #12343. That packet was closed for ownership collision rather than mechanics, and used an older V3.1 base. This carrier restarts from exact frozen V3.1 `508b342fc46fa91e3d7cdc3f0b7e44934a187c14` and hardens the two material proof gaps in the old helper: permissive type coercion/fallback timing and downstream-affordability coupling.

No `overlay/**`, config/default, package/builder, evaluator, opponent, or Kaggle submission file is changed.

## Gate before any promotion

Source safety is not an economics claim. Before any production wiring:

1. run an exact-package activation census and report every edited step/row/species/quantity;
2. prove terminal liquidation and every worker action are unchanged on activation cells;
3. run paired exact-V3.1 and representative-opponent cells and report `Δown`, `Δrival`, and `Δmargin = Δown - Δrival` plus every negative cell;
4. reject promotion if market-row/execution interactions create a material opponent benefit or any unexplained state divergence.

The focused suite is intentionally adversarial about config/step/quantity types, row positions, terminal liquidation, and later-spend funding. Hosted exact-head CI remains the authority for this branch.
