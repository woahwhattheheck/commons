# Gemini / Antigravity convergence

This package is the **coverage lock**, not a new gameplay controller.

The package now has two explicit provenance layers:

1. `GEMINI-ANTIGRAVITY.json` is the original 21-proposition master for the dense
   manifest / claim-board / metagame Antigravity stream.
2. `HISTORICAL-DIRECT.json` is the exhaustive direct-author audit of the same
   Antigravity identity in `#titan-kaggriculture`: 44 messages, paged 20 + 20 + 4,
   with every message classified as proposition, refinement, rollup, or
   coordination. It adds four genuinely distinct pre-manifest propositions that
   the original 21-entry lock omitted: analyzer margin hardening, high-quote FERT
   liquidation, terminal mass-hire, and WHEAT starvation / external-demand
   pressure.

Together they currently represent **25 distinct direct-author proposition
families**. Repeated discoveries and later corrections map back to the same
canonical proposition instead of minting duplicate V4 families. Coordination,
ownership, acknowledgement, and path-question posts remain in the 44-message
map with zero proposition IDs so “we scanned everything” cannot silently mean
“we discarded inconvenient non-mechanic posts from the denominator.”

`check_full_coverage.py` binds the two layers. It first validates the original
master through `check_ledger.py`, then proves that the 44-message direct-author
map is exact and that all 25 distinct proposition IDs are anchored by at least
one direct post.

A separate channel-wide Gemini-label sweep is still useful for model outputs
published under other swarm identities (for example MERIDIAN, Gemini Pro/Flash,
or imported Gemini artifacts). Those are **not** silently attributed to the
Antigravity author. They need their own authenticated provenance before being
folded into this package.

## Dispositions

Every proposition ends in one of four durable states and points at current V4
evidence:

- `SOURCE_REAL_CANDIDATE`: engine/source mechanism is real; policy value is still gated.
- `CORRECTED_DESCENDANT`: the useful mechanism survives, but Gemini's literal policy
  is replaced by a narrower source-safe form.
- `FALSIFIED`: the literal mechanism/policy is impossible or disproven and is fenced
  against resurrection without new evidence.
- `FIELD_BLOCKED`: a useful mechanism or intended descendant exists, but the current
  policy/source form is unsafe, cold, or source-unsound; a stronger successor contract
  is required before promotion.

## Direct historical additions

The four pre-manifest propositions are deliberately converged rather than revived
literally:

- **Analyzer ±65k clip** → keep finite-number validation, redundant-outcome
  consistency, and overflow-safe arithmetic; do not impose a guessed universal
  magnitude ceiling on legitimate current-engine margins. Any future bound must
  come from an authenticated producer contract and reject, not clip.
- **R04 FERT-LIQUIDATE threshold=25 / reserve=2** → the high-quote sale seam is
  source-real but the old magic threshold/reserve claim lacks current terminal
  evidence. It stays blocked until the incumbent seller/stockkeeper values quote,
  future fertilize obligations, shed pressure, market-prefix capacity and funding
  on current-native exposures.
- **Terminal mass-hire** → the daily Fibonacci reset is real, but blind 16-worker
  hiring is wrong. Canonical `terminal-labor-surge` admits only cash-funded marginal
  hands with executable productive work and terminal cash realization, and remains
  default-OFF pending paired field economics.
- **WHEAT starvation buyout** → literal stockout is false because BUY_PRODUCT has no
  WHEAT availability check; a self-only round trip is reversible. The useful
  descendant is external-demand price pressure, kept as a stress/gauntlet mechanism.

## Fail-closed custody

The registry/checkers are intentionally strict about both data and filesystem
surfaces:

- JSON is loaded with duplicate-key rejection at **every object depth**; a second
  `disposition`, `entries`, evidence field, or any other key cannot silently last-win.
- Non-finite JSON numbers are rejected.
- Evidence paths outside V4, containing `..`, or traversing literal
  `legacy/`/`superseded/` components are rejected.
- Every path component is checked with `lstat`; a symlink leaf or internal symlink
  ancestor cannot redirect canonical evidence into another subtree.
- Final evidence must be a regular file, resolve beneath the repository, and the
  resolved relative path is checked again for noncanonical ancestry.
- `FALSIFIED` and `FIELD_BLOCKED` entries require durable
  `do_not_repeat_without_new_evidence=true` fences.
- The direct-history scan query, author, sort order, 20/20/4 page counts, 44-message
  denominator, ordinal sequence, first/last timestamps, proposition IDs and all four
  historical additions are hard-gated.

## Important corrected forms

The coverage contract preserves negative information instead of forcing every
Gemini literal into runtime:

- `$1` FERT is destructive floor disposal, not a recoverable infinite warehouse.
- **MELON is currently FIELD_BLOCKED.** The crude sold-only cap was harmful, and the
  later purported repaired carrier still has executable-cardinality / whole-alternative
  source debt. Promotion requires producer-to-consumer executable custody, then
  current-native economics.
- Goose Printer's certified Day-0 frontier is 9 geese + one hire, not ten no-hire
  geese and not a proved cash printer.
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
- Shared EOD RNG frame advancement is real and lives in canonical TOWNRNG, but the
  opening weed pattern does not uniquely reveal the hidden seed.
- EGG's log curve is unusually resilient but finite; EGG cannot be directly bought
  out of the market.
- Apex counterplay keeps authenticated clone-latch/Strawberry timing evidence and
  rejects the exaggerated massive-FERT-sponge branch.

## Validation

From this directory:

```bash
python -B -m unittest -q test_check_ledger.py test_full_coverage.py
python -O -B -m unittest -q test_check_ledger.py test_full_coverage.py
python -m py_compile check_ledger.py check_full_coverage.py test_check_ledger.py test_full_coverage.py
python check_ledger.py
python check_full_coverage.py
```

The synthetic contract surface is currently **31 adversarial tests**: 18 for the
master ledger trust boundary and 13 for direct-author completeness. The latter
include missing/duplicate message ordinals, scan-denominator drift, unknown
proposition IDs, proposition laundering through coordination rows, missing
historical entries/evidence, unfenced blocked descendants, and loss of any one of
the 25 distinct proposition anchors.

The last two commands are current-checkout gates and additionally require every
canonical evidence path in the real V4 tree to exist.

This package changes no gameplay/runtime source, feature default, config,
COMPOSITION, INTEGRATION, archive, evaluator, provider, or Kaggle state. Existing
mechanism owners retain source, policy, and economics authority. Historical direct
coverage lives in this same package as a consolidation layer; it is not a competing
controller or truth registry.
