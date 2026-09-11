# TITAN V3.1 final submission tuple contract donor

This directory is **analysis/tooling only**. It exists to stop the last score-facing
transform from silently dropping, manufacturing, or normalizing away upstream V3.1 work.

## Provenance / topology

- immutable donor parent: `6e5e3c7cc5302d6db4b702cc4fd7c8ca721d7b8a` (#12535 predecessor)
- live P0 successor at this revision: `0fc8ea0d399a9506873f7249415e2491db2ff565`
  (workflow-only custody advance; gameplay/package bytes unchanged)
- shipped gameplay ancestor: `8e3d92a286806f9f9525973ee7d359b629a11487`
- reviewed score-transform donor: #12505 @ `dd41984ec477d6a1b07bbab2779a2e9f54f879c4`
- reviewed `make_submission.py` blob: `9c5e46428f0a2357d7db6e46c4aa5f1f4748717d`

The branch intentionally remains an immutable analysis donor rather than rebasing simply
because P0 custody moved. Production authority must be established later on the literal
assembled parent.

The #12505 transform has one desirable structural property: it decodes the whole
`TITAN-CONFIG.json`, changes only score-facing values, and serializes the complete mapping
again. Therefore future keys are naturally preserved. Its old precondition contract is too
weak for the final V3.1 assembly, however: it does not bind B5 CARROT, B5 JIT, strict
row-shed activation, the complete held R04 context, or the literal L3 threshold.

## Final input theorem

A future post-#12565 / post-cattle-OFF / post-strict-row-shed consumer may use this donor
only when its input package exact-type satisfies the **held H8 assembly**:

- `r04_sale_window is False`;
- `r04_sale_horizon == 8` with exact non-bool integer type;
- `r04_open_roundtrip == 0` with exact non-bool integer type;
- `r04_row_order is True` (row-shed must not be certified while inert);
- `r04_evening_flush is True`;
- `r04_sale_fertilizer is True`;
- `r04_cattle_early is False`;
- `r04_kill_late_water is False`;
- `r04_strawberry_endgame is False`;
- `r04_strawberry_max_plants == 8` with exact integer type;
- `r04_strawberry_topup is True` (H4);
- `r04_no_late_sale_advance is True` and
  `r04_no_late_sale_advance_step == 648` with exact integer type;
- `r04_b5_carrot_fertilizer is True`;
- `r04_b5_jit_fertilize is True`;
- `r04_row_shed is True`.

This tuple deliberately makes the LAST transform incapable of deciding gameplay. If a
later reviewed H13/H10/other horizon or another R04-context winner replaces H8, that
upstream decision must first update this theorem and its final-stack receipt; the
submission step may not silently force it back to H8.

## Exact score-facing post-state

For the currently held H8 theorem the transform may set only:

- `r04_sale_window = True`;
- `r04_sale_horizon = 8` (idempotent preservation, not a new horizon decision);
- `r04_sale_fertilizer = True` (idempotent preservation);
- `r04_cattle_early = False` (idempotent preservation).

Therefore the actual H8 configuration-value delta at the last step is exactly
`r04_sale_window: False -> True`. The contract separately checks the exact post-state;
it does not rely only on the weaker rule that transform-owned keys are exempt from the
non-score preservation check.

Every other configuration key/value and every non-config package byte must survive
unchanged. `r04_row_shed`, ROW_ORDER, evening flush, opening context, B5/JIT, H4 and L3
are preconditions/preservation witnesses, not transform-owned values.

## Authority boundary

This donor is deliberately not wired into `make_submission.py`, `apply_v3.py`, package
metadata, defaults, provider code, Kaggle, or any workflow. It creates **zero Actions
fanout** and has no submission or merge authority.

Once #12565 reaches its literal final L3 head and the reviewed #12551-semantics row-shed
consumer is composed with cattle OFF (plus any separately selected optional factors), the
**same last-stage #12505 transform lineage** should consume this theorem on the literal
assembled package. That consumer must bind the chosen final horizon/context, run the
contract under normal and optimized Python, prove only `TITAN-CONFIG.json` changes at the
package-member level, prove every unrelated config type/value remains identical, and
recheck current parent/canonical/head freshness after spend. Do not create a sibling
submission architecture from this analysis module.
