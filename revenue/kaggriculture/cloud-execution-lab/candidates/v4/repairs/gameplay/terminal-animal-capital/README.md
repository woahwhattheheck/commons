# H5 terminal animal-capital guard — V4 recovery

This package recovers the narrow, source-grounded portion of V3.1 H5
(PR #12471) into the single V4 research/repair tree.  It is **default off**
and is not wired into the production runtime.

## Mechanism

The current official engine defines first animal production at 4 days for a
GOOSE, 6 for a SHEEP, and 8 for a COW.  `BUY_ANIMAL` executes in the market
phase after unit actions, so a newly purchased animal cannot be placed before
a later callback.  The guard deliberately grants an even earlier, same-day
placement bound; if first production is still beyond the last executable
action under that optimistic bound, the purchase cannot create product before
termination.

The only permitted edit is replacing an eligible `BUY_ANIMAL` market row with
`[]`, preserving the raw market vector length.  It applies only from the
final-plan window (step 648) and only under the exact standard 24-turn,
720-step timing contract.

Saved cash can make later market orders newly executable.  Therefore H5 edits
only the provably-dead animal-buy suffix after the last other non-SELL,
non-placeholder market row.  Every worker command, SELL row and quantity,
HIRE, BUY_LAND, BUY_SEED, BUY_PRODUCT, unknown order, and unknown animal is
parent-owned.

## Provenance and stricter V4 boundary

Historical donor: PR #12471 head
`808f7f4329ccae2656b14fb88794682cb7b3adbc`, source Git blob
`ef02024d04ab554ed781d9af5a427436edf6e868`.

Official-engine source identity at recovery:
`reference/engine/kaggriculture.py` Git blob
`3c202c7ee921da239356789e266b694635103fc4`.

Unlike the historical donor, the V4 component does **not** assume omitted
timing keys mean defaults.  Missing, bool/float/string-poisoned, or nonstandard
`turnsPerDay` / `episodeSteps` fail closed to the exact input action.

## Authority boundary

Source/mechanism only until a current-native route census proves natural late
`BUY_ANIMAL` engagement.  Zero engagement terminalizes the lane without
runtime wiring.  If it engages, the next gate must prove both-seat execution,
unchanged unit/liquidation behavior, saved terminal cash, paired own/rival
money and margin, and no harmful externality across representative opponents.
No default/config/archive/Kaggle change is authorized here.
