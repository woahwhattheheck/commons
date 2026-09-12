# Gemini / Antigravity convergence

This package is the **single coverage lock**, not a gameplay controller.

Gemini produced more than the 2026-09-12 Antigravity board. The current lock therefore has two machine-checked source ledgers inside this one authority:

- `GEMINI-ANTIGRAVITY.json` — the original 21 fleet-board/direct-metagame propositions from the dense Antigravity wave;
- `LEGACY-GEMINI.json` — 15 older TESSERA/G01, MERIDIAN, pro-capital, flash-market and idle-hands propositions that predate the board or arrived in separate handoffs.

`check_ledger.py` now requires **both** ledgers and fails unless all 36 distinct propositions remain represented. `LEGACY-GEMINI.json` also carries the mandatory current override for `gemini.demand-velocity`, so merged PR #13018 (`DEMAND-VELOCITY.md` / `demand_velocity.py`) supersedes the earlier mean-only baseline evidence without rewriting the historical 21-entry ledger.

Every proposition terminates in exactly one durable disposition and points only at **current regular files under `candidates/v4`**:

- `SOURCE_REAL_CANDIDATE`: engine/source mechanism is real; policy value is still gated.
- `CORRECTED_DESCENDANT`: the useful mechanism survives, but the literal Gemini policy is replaced by the narrower source-safe form.
- `FALSIFIED`: the literal mechanism/policy is impossible or disproven and is fenced against resurrection without new evidence.
- `FIELD_BLOCKED`: source mechanism or lineage is real, but the attempted policy is unsafe, cold, unrecovered, or lacks the source theorem required for runtime use.

A merged/closed historical PR is **provenance, not canonical evidence**. `canonical_evidence` must exist now in the one V4 tree; paths under `legacy/` or `superseded/` are rejected. Failed ideas cannot disappear from the ledger to make the suite green.

## Antigravity corrected forms

The original board retains its important negative information:

- `$1` FERT is destructive floor disposal, not a recoverable infinite warehouse.
- MELON uses committed-production custody (sold + held + live future yield), not the harmful sold-only hard cap.
- Goose Printer's certified Day-0 frontier is 9 geese + one hire, not ten no-hire geese and not a proved cash printer.
- Intermittent starvation is CARE-aware and must guarantee the next feed; blanket alternate-day starvation destroys CARE value.
- HYDRA's final `WATER -> PASS` rewrite is field-blocked; a successor must spend the slot productively and bind next-day WATER recovery.
- Carried inventory is a real intraday custody surface, but current raw routes have no safe CARRYBANK admission after acquisition/custody checks.
- Zero-cash structures are not zero-action structures. Blanket weed carpets are rejected; productive structures may still carry measured weed/RNG side effects.
- Direct TOMATO/EGG/CARROT `BUY_PRODUCT` squeezing is impossible. WHEAT/FERT pressure remains a separate, source-valid market domain.
- Shared EOD RNG frame advancement is real and lives in canonical TOWNRNG, but the opening weed pattern does not uniquely reveal the hidden seed.
- EGG's log curve is unusually resilient but finite; EGG cannot be directly bought out of the market.
- Apex counterplay keeps authenticated clone-latch/Strawberry timing evidence and rejects the exaggerated massive-FERT-sponge branch.

## Legacy Gemini lineage now covered

### TESSERA / G01

- **Row-shed final-day SELL ordering** survives as canonical STRATUM. Historical V3 evidence was strong, but V4 activation still requires the distinction to survive downstream market-pressure composition and current-native both-seat economics.
- **E11 rival SELL deferral** survives only with exact integer future town absorption. Fractional absorption multipliers are retired; TOWNSELL is the stronger deterministic post-drain theorem.
- **O01 rival archetypes** are retired as mutually exclusive intent labels. Public expansion, visible standing yield, public price movement and known town drain remain independent PARALLAX evidence.
- **E20 HIRE guard** survives only with the executable-market-prefix repair. The broad HIRE economics lane is not promoted merely because the source guard exists.
- **E20/shop-arbitrage 1.5x absorption** is replaced by exact unlocked-shop drain and the source-bound DEMANDVEL distribution.
- The recovered **legacy opening tape** is a solvency falsifier: 882 spend from 1000 leaves 118, not the claimed 498.
- The historical row-shed commit explicitly excluded **day-28/29 skips + glut bleed**. No byte-exact semantics were recovered; broad repeated terminal-sale experiments were harmful. This remainder stays blocked rather than guessed.

### MERIDIAN

- **Identical-prefix adaptive sale recourse** is retained as negative ancestry. Merged PR #10004 reached a real WOOL suffix, but on its eight development games static/adaptive each lost 7 own cash per seat versus the integrated control; no strength promotion survived.
- **Cross-product hidden-inventory cash/mass-balance reconstruction** remains blocked. Current PARALLAX deliberately reads public farm/market/town state and does not infer rival private shed inventory. No exact current-V4 cross-product cash certificate was recovered, so the lock forbids filling that gap with an invented private-state oracle.

### pro-capital / flash-market

- **pro-capital** routes to the existing early-capital authority plus KESTREL lockstep admission. Capital promotion may not sacrifice an original executable operating purchase.
- **flash-market** routes to exact town-event timing. TOWNSELL proves when a known intervening town drain improves the proceeds of the same already-authored sale under its stated zero-rival-flow premise; there is no generic fixed-clock merchant.

### idle-hands handoff

- **PASS / spare service -> CARE** routes to S8/AFTERCARE/CARESAT. CARE can create later value, but delayed production and held/shed capacity make unconditional conversion unsafe.
- **redundant FEED -> CARE** is not killed by the old 7,192-FEED callback-entry census. Current W2 proves the distinct same-turn case where an earlier actor FEEDs and a later same-site FEED becomes redundant; the current source component remains engagement/economics gated.
- **WHEAT FERTILIZE** routes to WF1. Its current-native 8-cell receipt has 8 positive margin cells, no negative cells, mean margin delta +143.25 and first action divergence at step 647, while explicitly withholding activation authority.
- **buy WHEAT / buy GEESE because a hand is idle** is corrected into normal procurement/acquisition economics. Spare labor is evidence, not proof that a purchase pays after cash, placement, feed, service, carry/shed and sale obligations.

## DEMANDVEL upgrade

The legacy supplement requires merged #13018 as the current descendant of `gemini.demand-velocity`:

- exact expected drain per random shop-instance tick: WHEAT .625, STRAWBERRY .50, CARROT/MILK .375, TOMATO/EGG/WOOL .25, MELON/FERTILIZER 0;
- unlock horizons and town-center drain are added before calling this an episode demand expectation;
- the canonical 100-seed baseline exposes low-quantile absorption risk rather than converting means into hard crop quotas;
- `conservative_headroom()` remains explicitly non-authoritative for crop choice, sale timing and rival supply.

This is intentionally stronger than a hard demand tier while remaining composable with existing production/sale owners.

## Validation

From this directory:

```bash
python test_check_ledger.py
python -O test_check_ledger.py
python check_ledger.py
```

The first two runs exercise the checker against a synthetic repository surface. The final command is the current-checkout gate: it validates both ledgers, the mandatory DEMANDVEL override and every canonical evidence path in the real V4 tree.

This package changes no runtime source, feature default, config, COMPOSITION, archive, evaluator, provider, or Kaggle state. Existing mechanism owners retain policy/economics authority.