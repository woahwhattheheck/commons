# Intraday market contracts — independent acceptance companion

## Delivery status

**Built and executed locally; NOT posted to Slack and NOT committed or merged.**
The current session exposed GitHub/Slack read actions but no posting or repository
write actions; plugin discovery confirmed the existing installations, not an
additional usable write path. No remote claim was posted. No peer was instructed
or notified by this session.

This is an additive acceptance companion for ASTRA-GRANDE's live intraday inventory /
scarcity / market-removal work. It is not another strategy driver, controller,
observer, V4 root, or promotion decision. The proposed destination is the existing
`main:revenue/kaggriculture/cloud-execution-lab/candidates/v4/research/lockstep-scale/`
family. GRANDE and the established forward-buy, F4/C6, and wheat_merchant owners
retain their implementations. All source in the patch is new; no existing source
or manifest is replaced.

## Provenance

- Canonical authority read at commit `9e2574224bc970c7ac19a592c8702fb8ae660ee5`:
  `candidates/v4/CANONICAL.json` names **main**, not `titan/v4-20260911`.
- Existing checked package downloaded through GitHub artifact `10175943272`.
- Inner native archive: `b567942e4fb4e0571ebf9f8eaaf143d4a9156df3289f09a98db37823ef4d68d9`.
- A fresh live-main `runtime/integrated-selected/CURRENT-ARCHIVE.json` read still
  names that exact archive. This verifies the declared archive identity, not all
  unactivated repair sources accumulated on main.
- Pinned interpreter SHA256:
  `bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e`.
- Interpreter Git blob: `3c202c7ee921da239356789e266b694635103fc4`;
  matches the live repository source read.
- The original existing evaluator and loader execute the full official interpreter.
  No alternate game transition implementation is used in green controls.
  Their hashes and the engine's three-file identity check are in each receipt.
- Tested with the Python version recorded in the receipts (3.13 in this session).
  Python 3.11, hosted Kaggle, and native `main.py::agent` integration are **not**
  claimed tested here.

## Executed results

Each green mode: **18/18 tests, 148 initializations, 232 completed transitions**,
zero test errors or skips. Both ordinary Python and `python -O` pass. Counts are
for one complete suite, not a claim of 380 complete games. The negative runner
reexecutes a green control before the faults in each mode.

All **9/9 semantic faults in each mode** are rejected through assertions, not
import errors, timeouts, or source-pin rejection. The faults deliberately allow
unsupported product buys, add a false inventory stockout, use the wrong buy
quote, ignore shed capacity, cap carried inventory, remove EOD discard, admit
floor-price sales, move town consumption before market, or cap pickup quantity.
Mutant function source is modified only in memory and its hash is recorded.
The pinned engine files remain unchanged.

A separate runner-only stale-receipt control also passes: a deliberately stubbed
child exits without writing its output, and the driver refuses to reuse an old
receipt. That stub tests CLI failure handling, not game semantics; it adds no
engine-test or gameplay counts.

### Mechanical boundaries

1. `BUY_PRODUCT` fills only WHEAT and FERTILIZER. The parser accepts the syntax of
   other products, but the market execution stage rejects those purchases. Across
   both seats, buying 5,000 CARROTs/TOMATOes/EGGs with ample synthetic cash fills
   **zero**. A large hypothetical scarcity quote does not provide an executable
   way to acquire those goods.
2. WHEAT/FERTILIZER buys still fill when market inventory is zero or negative,
   provided cash and shed space suffice. This rules out *hard stockout* as the
   wheat-denial mechanism, not affordability pressure. In the constructed animal
   case, a cow survives at zero market inventory with $125 available for feed;
   at $124 the feed purchase fails and the already-neglected animal escapes.
3. At initial WHEAT prices, a $3,000 wallet buys **95 units**, not the requested
   5,000; $5 remains. A $3,000 FERTILIZER wallet buys 29 units; $13 remains.
4. Unit actions precede market purchases. A PICKUP cannot collect the product
   purchased in the same callback. Funded repeated PICKUP/BUY does accumulate
   **500 WHEAT carried plus 100 in the shed in six callbacks**, costing $24,800.
5. The tested 24-callback hoard buys 2,400 WHEAT and spends $138,439. Without
   liquidation, end-of-day retains only 100 and discards 2,300. This is a
   deliberately funded constructed boundary, not a reachable opening policy.
6. `PLACE` preserves excess cargo when the shed is full; `DROP` destroys excess.
   Cargo cannot be sold until deposited. A constructed PLACE/SELL unwind empties
   the warehouse without loss. Same-turn sales occur too late to save overflow
   already discarded by a DROP.

### Positive controls — not a blanket strategy rejection

- An unchanged-market, single-player BUY/SELL round trip is cash neutral in the
  tested non-floor grid: 48 configurations across both seats. At the fertilizer
  floor it remains cash neutral but market inventory need not be restored,
  because $1 sales are not admitted to market inventory.
- **+64 own cash** in either seat: buy 100 WHEAT immediately before a known tick
  from eight BAKERY copies, sell the next callback. Entry cost is $3,170; final
  own inventory is zero. The no-shop control returns $0. A simultaneous rival
  sale on exit reverses the gain in the tested countercontrol.
- **+1,010 own cash** in either seat: buy 100 FERTILIZER in lockstep with a rival
  buying 100, then sell ours in the following market slot. Final own inventory
  is zero; the rival still owns its 100 units. This is a funded, scripted rival
  response, **not a cash-margin or equal-asset advantage**, and not an observable
  guarantee of a rival's next hidden action.

These controls preserve the live research direction: funded exposure to known
town demand or anticipated rival flow. They do not prove natural engagement,
competitive profit, a winning policy, or grounds to activate anything by default.

## Reproduction

Use an already extracted, trusted canonical archive. From repository root:

```sh
CHECK=revenue/kaggriculture/cloud-execution-lab/candidates/v4/research/lockstep-scale
RUNTIME=/path/to/extracted/titan-current
python "$CHECK/check_intraday_market_contract.py" \
  --runtime-root "$RUNTIME" --output /tmp/intraday-normal.json
python -O "$CHECK/check_intraday_market_contract.py" \
  --runtime-root "$RUNTIME" --output /tmp/intraday-optimized.json
python "$CHECK/check_intraday_market_mutants.py" \
  --runtime-root "$RUNTIME" --output-dir /tmp/intraday-negative-controls
```

The engine hash mismatch is a hard stop. The acceptance checker returns zero only
for a green suite; the mutation driver returns zero only when each mode's green
control passes and every injected fault is assertion-rejected without errors.
No network calls, paid compute, owner-PC execution, workflow dispatch, production
archive rewrite, config/default flip, or Kaggle submission is part of these commands.
The runtime path must be supplied; the checker never downloads missing sources.

## Source references

- Canonical authority:
  https://github.com/woahwhattheheck/commons/blob/9e2574224bc970c7ac19a592c8702fb8ae660ee5/revenue/kaggriculture/cloud-execution-lab/candidates/v4/CANONICAL.json
- Official engine copied into the existing package:
  https://github.com/woahwhattheheck/commons/blob/9e2574224bc970c7ac19a592c8702fb8ae660ee5/revenue/kaggriculture/cloud-execution-lab/reference/engine/kaggriculture.py
- GRANDE's live claim and results thread, read but not posted to by this session:
  https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1789183321435249
