# DROPSTAGE — capacity-preserving manual DROP staging

Status: **engine theorem proven; natural donor/current witness unresolved; no runtime admission**.

DROPSTAGE isolates one official-interpreter asymmetry that is useful to the sole canonical TITAN V4 line without creating another scheduler or runtime fork. A manual `DROP` can fill only the shed's current free capacity and then clear the actor's carried input, destroying overflow before the later market phase can create room. An item-bounded `PLACE item qty` deposits the same immediately admissible quantity but subtracts only what actually moved, preserving the remainder in carry.

## Source authority

The oracle fails closed on the exact official engine Git blob `3c202c7ee921da239356789e266b694635103fc4` and exact 13x719 donor tape blob `a43289b9cc5e34a2481fddf652762a7d92f427ef`.

The theorem is intentionally narrower than the existing CARRYBANK and SHEDRELAY work:

- CARRYBANK hoists shed inventory into carry and requires a proved same-day consumption sink; DROPSTAGE starts from inventory already carried by the actor.
- SHEDRELAY proves same-callback shed handoff and records the partial-capacity DROP hazard; DROPSTAGE does not create actor-to-actor relays.
- B7/capacity guards remain authoritative for ordinary DROP safety. DROPSTAGE is not a generic DROP rewrite.

## Exact semantic witness

For one actor carrying 3 units, with only 1 shed slot free before units and at least 2 guaranteed slots free after the complete market phase:

- manual `DROP`: 1 reaches the shed, 2 are destroyed immediately;
- staged `PLACE item 3`: the same 1 reaches the shed before market, so the market starts from the same shed state; 2 remain carried;
- on the final callback of the day, if post-market room is proved sufficient, EOD return preserves those 2.

The pure receipt therefore reports `saved_units = 2` and `market_start_shed_delta = 0`.

## Fail-closed admission rule

`admit_dropstage(...)` emits a replacement only when every proof obligation is supplied:

1. exactly one carried item has positive quantity;
2. current shed room is smaller than that quantity, so the original DROP is actually lossy;
3. the callback is the final callback of the day;
4. the caller has positively proved `PLACE` support for that item;
5. a lower bound on room **after the complete market phase** is supplied;
6. that lower bound fits the entire staged remainder **plus all other actors' EOD carry obligations**.

The last condition prevents a fake rescue that merely moves overflow loss onto another actor. Missing, malformed, partial, or merely optimistic proof inputs return `None`.

## Natural-source census

`donor_drop_census()` inventories authored `DROP`/`PLACE` syntax in the authenticated donor bank. Static syntax is not enough to assert dynamic loss: any authored DROP must still be replayed against the exact engine to prove carried quantity, pre-unit shed room, complete market postimage, competing EOD carry, and economic effect. Therefore the package state is `THEOREM_PROVEN_NATURAL_REPLAY_REQUIRED`, not a promotion claim.

No runtime/default/config/COMPOSITION/INTEGRATION/archive/Kaggle bytes are changed by this package.

## Tests

From this directory:

```bash
python -B test_dropstage_oracle.py
python -O -B test_dropstage_oracle.py
python -m py_compile dropstage_oracle.py test_dropstage_oracle.py
```

The focused suite covers the exact 3/1/3 witness, market-start identity, full non-crowding rescue, partial-room rejection, competing-EOD-carry rejection, multi-item rejection, already-lossless DROP rejection, non-EOD rejection, unproved PLACE support, and malformed-input fail-closed behavior.

## Promotion gate

Re-open runtime admission only after an authenticated natural current-postimage replay produces an output-changing lossy DROP witness and a paired exact-engine gate shows that the staged replacement improves own terminal economics without rival harm, route displacement, or any new DROP/EOD loss. Until then, activation remains OFF.
