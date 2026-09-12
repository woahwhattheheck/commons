# Gemini / Antigravity convergence

This package is the **coverage lock**, not a new gameplay controller.

Gemini/Antigravity produced a dense burst of Kaggriculture mechanics in Slack: the
15-item fleet claim board plus direct-post-only metagame ideas (Apex clone
conditioning/counter-ambush, direct short squeeze, shared-RNG frame advancement,
opening seed cracking, and EGG elasticity). Parallel workers proved, repaired,
falsified, or field-blocked them across several canonical V4 authorities.

`GEMINI-ANTIGRAVITY.json` makes that convergence explicit. Every distinct
proposition has exactly one durable disposition and points only at **current,
regular, non-symlink files under `candidates/v4`**:

- `SOURCE_REAL_CANDIDATE`: engine/source mechanism is real; policy value is still gated.
- `CORRECTED_DESCENDANT`: the useful mechanism survives, but Gemini's literal policy
  is replaced by a narrower source-safe form.
- `FALSIFIED`: the literal mechanism/policy is impossible or disproven and is fenced
  against resurrection without new evidence.
- `FIELD_BLOCKED`: a useful mechanism or intended descendant exists, but the current
  policy/source form is unsafe, cold, or source-unsound; a stronger successor contract
  is required before promotion.

## Fail-closed custody

The checker hard-codes the complete 21-proposition ID set. Removing a failed idea
from the JSON does **not** make the suite green; missing IDs fail. A closed or
merged PR also does not count as evidence: each `canonical_evidence` path must
exist *now* in the canonical V4 tree.

The registry is intentionally strict about its own input and filesystem surface:

- JSON is loaded with duplicate-key rejection at **every object depth**; a second
  `disposition`, `entries`, evidence field, or any other key cannot silently last-win.
- Non-finite JSON numbers are rejected.
- Evidence paths outside V4, containing `..`, or traversing literal
  `legacy/`/`superseded/` components are rejected.
- Every path component is checked with `lstat`; a symlink leaf or an internal symlink
  ancestor alias cannot redirect canonical evidence into another subtree.
- The final evidence target must be a regular file, resolve beneath the repository,
  and the resolved relative path is checked again for noncanonical ancestry.
- `FALSIFIED` and `FIELD_BLOCKED` entries require durable
  `do_not_repeat_without_new_evidence=true` fences.

## Important corrected forms

The coverage contract deliberately preserves negative information:

- `$1` FERT is destructive floor disposal, not a recoverable infinite warehouse.
- **MELON is currently FIELD_BLOCKED.** The crude sold-only cap was harmful, and the
  later purported repaired carrier still has two source debts: shallow outer metadata
  shrink can leave executable `variants[*].patches` intact, and a shared budget across
  FourthQuadrant proposals is invalid because those proposals are mutually-exclusive
  alternatives. Promotion now requires executable MELON cardinality per whole proposal,
  no cross-alternative decrement, canonical custody rebind, then current-native economics.
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
python -B -m unittest -q test_check_ledger.py
python -O -B -m unittest -q test_check_ledger.py
python -m py_compile check_ledger.py test_check_ledger.py
python check_ledger.py
```

The synthetic contract suite currently contains 18 adversarial tests, including
predecessors for duplicate root/nested JSON keys, leaf and ancestor symlinks,
stale ancestry, and premature MELON promotion. Run it in both normal and `-O`
mode. The final `python check_ledger.py` is the current-checkout gate and also
requires every canonical evidence path in the real V4 tree to exist.

This package changes no gameplay/runtime source, feature default, config,
COMPOSITION, INTEGRATION, archive, evaluator, provider, or Kaggle state. Existing
mechanism owners retain source, policy, and economics authority; in particular,
the active MELON source repair remains owned by the existing
`antigravity-melon-cap` lineage rather than this coverage package.
