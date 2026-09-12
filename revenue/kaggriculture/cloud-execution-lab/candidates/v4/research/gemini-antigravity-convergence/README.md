# Gemini / Antigravity convergence

This package is the **coverage lock**, not a new gameplay controller.

Gemini/Antigravity produced a dense burst of Kaggriculture mechanics across the
older MERIDIAN/Gemini stream and the later Antigravity fleet posts. Parallel
workers correctly proved, repaired, falsified, or field-blocked many of them,
but the results landed across multiple canonical V4 research/repair authorities.

`GEMINI-ANTIGRAVITY.json` makes that convergence explicit. Every distinct
proposition has exactly one durable disposition and points only at **current
regular files under `candidates/v4`**:

- `SOURCE_REAL_CANDIDATE`: engine/source mechanism is real; policy value is still gated.
- `CORRECTED_DESCENDANT`: the useful mechanism survives, but Gemini's literal policy
  is replaced by the narrower source-safe form.
- `FALSIFIED`: the literal mechanism/policy is impossible or disproven and is fenced
  against resurrection without new evidence.
- `FIELD_BLOCKED`: source mechanism is real, but current-native execution shows the
  attempted policy form is unsafe/cold; a stronger successor contract is required.

The checker hard-codes the complete proposition ID set. Removing a failed idea
from the JSON does **not** make the suite green; missing IDs fail. A closed or
merged PR also does not count as evidence: each `canonical_evidence` path must
exist *now* as a regular file in the canonical V4 tree, and `legacy/` or
`superseded/` ancestry is rejected.

## Important corrected forms

The coverage contract deliberately preserves negative information:

- `$1` FERT is destructive floor disposal, not a recoverable infinite warehouse.
- MELON is a source-HOLD until whole executable proposal cardinality and realization
  custody are correct; shallow metadata shrink or cross-alternative budget spending
  is not a valid repair.
- Goose Printer's certified Day-0 frontier is 9 geese + one hire, not ten
  no-hire geese and not a proved cash printer.
- Intermittent starvation is CARE-aware and must guarantee the next feed; blanket
  alternate-day starvation destroys CARE value.
- HYDRA's final `WATER -> PASS` rewrite is field-blocked; a successor must spend
  the slot productively and bind next-day WATER recovery.
- Carried inventory is a real intraday custody surface, but current raw Arlene
  routes have no safe CARRYBANK admission after acquisition/custody checks.
- Zero-cash structures are not zero-action structures. Blanket weed carpets are
  rejected; productive structures may still carry measured weed/RNG side effects.
- Direct TOMATO/EGG/CARROT `BUY_PRODUCT` squeezing is impossible. WHEAT/FERT
  pressure remains a separate, source-valid market domain.
- Shared EOD RNG frame advancement is real and now lives in canonical TOWNRNG,
  but the opening weed pattern does not uniquely reveal the hidden seed.
- EGG's log curve is unusually resilient but finite; EGG cannot be directly
  bought out of the market. Timing evidence must bind the moved EGG sale's own
  filled units and sale cash, not unrelated downstream spending.
- Apex counterplay keeps authenticated clone-latch/Strawberry timing evidence and
  rejects the exaggerated massive-FERT-sponge branch.
- DEMANDVEL's best form is the current source-bound absorption-headroom oracle in
  `market-baseline/DEMAND-VELOCITY.md` and `demand_velocity.py`, not static tiers.

## Legacy Gemini / direct-post coverage that must not disappear

These proposition families predate or sit outside the original 21-item Antigravity
manifest. They are first-class coverage IDs in the canonical ledger rather than a
second registry.

### Terminal mass-hire

The literal "spam all terminal HIREs" idea is not a free score conversion: HIRE
cost is paid from terminal cash and grows with same-day hiring. The useful form is
TERMINUS: admit only jobs whose authenticated remaining executable work repays the
marginal wage by terminal. Canonical evidence lives in
`repairs/gameplay/terminal-labor-surge/`; blind mass-hire is not resurrected.

### WHEAT market denial / starvation

The Antigravity hard-denial premise is false: `BUY_PRODUCT WHEAT` does not create a
hard market-unavailability state and the market can cross through zero inventory.
The useful residue is timed forward procurement / rival-flow exposure. Constructed
full-interpreter carry work shows unchanged-market round trips can be neutral while
town demand or rival flow changes realized economics, and current TOWNPROCURE is a
separate receipt-safe retiming descendant. This proposition must therefore be kept
as corrected pressure/procurement, not confused with intermittent animal starvation.

### FERT high-quote liquidation

`R04-FERT-LIQUIDATE` is distinct from the falsified `$1` warehouse. Selling surplus
FERT at a high public quote is mechanically real, but the measured gate was noisy
and largely redundant with canonical liquidation, so it is FIELD_BLOCKED rather
than promoted or erased. Any revival must beat the incumbent seller on exact
returned actions and paired economics.

### MERIDIAN hidden-inventory / maximin

Private rival stock cannot be reconstructed from public inventory by wishful mass
balance. The surviving form is public-state pressure: bound only what public supply,
prices, town drains and authenticated route evidence prove. No hidden-private oracle
may be inferred from the MERIDIAN hypothesis.

### MERIDIAN identical-prefix adaptive recourse

The adaptive-recourse experiment reached its intended WOOL suffix but did not beat
its static/control alternative; the historical #10004 result is negative ancestry,
not current activation authority. The canonical disposition is FIELD_BLOCKED until
a new public observation creates a genuinely decision-changing suffix advantage.

### Gemini pro-capital

The useful descendant is KESTREL/early-capital: reorder capital only under exact
engine-active prefix and rival-lockstep non-regression custody. "Spend earlier" by
itself is not policy authority. Current evidence is
`repairs/gameplay/early-capital/KESTREL-LOCKSTEP.md`.

### Gemini flash-market

The literal timing intuition survives as TOWNFLASH/TOWNSELL source theorems: market
orders execute before town drains, so identical buys/sells can differ around exact
town events. It is a source-bound timing feature, not permission to hard-code one
clock or ignore row alignment, cash path, or downstream obligations.

### Idle-hands bundle

Gemini's broad "replace idle PASS" family decomposes into existing owners instead
of one mega-controller: GOOSE CARE belongs to S8/AFTERCARE/CARESAT; WHEAT
FERTILIZE belongs to WF1/production service; feed/procurement stays in feed and
TOWNPROCURE authorities; animal acquisition stays HOMESTEAD/HERDWORK. The W2
redundant-FEED salvage branch had no current reachable evidence and must not be
promoted just because PASS exists.

## Validation

From this directory:

```bash
python test_check_ledger.py
python -O test_check_ledger.py
python check_ledger.py
```

The first two runs exercise the checker against a synthetic repository surface.
The final command is the authoritative current-checkout gate: it additionally
requires every canonical evidence path in the real V4 tree to exist.

This package changes no runtime source, feature default, config, COMPOSITION,
archive, evaluator, provider, or Kaggle state. Existing mechanism owners retain
policy/economics authority.