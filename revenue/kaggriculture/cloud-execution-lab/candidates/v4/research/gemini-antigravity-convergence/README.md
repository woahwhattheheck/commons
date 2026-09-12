# Gemini / Antigravity convergence

This package is the **coverage lock**, not a new gameplay controller.

Gemini/Antigravity produced a dense burst of Kaggriculture mechanics in Slack: the
15-item fleet claim board plus direct-post-only metagame ideas (Apex clone
conditioning/counter-ambush, direct short squeeze, shared-RNG frame advancement,
opening seed cracking, and EGG elasticity). Parallel workers correctly proved,
repaired, falsified, or field-blocked many of them, but the results landed across
multiple canonical V4 research/repair authorities.

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
- MELON uses committed-production custody (sold + held + live future yield), not
  the harmful sold-only hard cap.
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
  bought out of the market.
- Apex counterplay keeps authenticated clone-latch/Strawberry timing evidence and
  rejects the exaggerated massive-FERT-sponge branch.

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
