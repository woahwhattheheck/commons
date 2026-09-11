# TITAN V3.1 final submission tuple contract donor

This directory is **analysis/tooling only**.  It exists to stop the last score-facing
transform from silently dropping or accepting stale upstream V3.1 work.

## Provenance / topology

- current repaired custody parent: `6e5e3c7cc5302d6db4b702cc4fd7c8ca721d7b8a` (#12535)
- shipped gameplay ancestor: `8e3d92a286806f9f9525973ee7d359b629a11487`
- reviewed score-transform donor: #12505 @ `dd41984ec477d6a1b07bbab2779a2e9f54f879c4`
- reviewed `make_submission.py` blob: `9c5e46428f0a2357d7db6e46c4aa5f1f4748717d`

The #12505 transform has one desirable structural property: it decodes the whole
`TITAN-CONFIG.json`, changes only score-facing values, and serializes the complete
mapping again.  Therefore future keys are naturally preserved.  Its old precondition
contract is too weak for the final V3.1 assembly, however: it does not require or report
B5 CARROT, B5 JIT, row-shed, or the literal L3 threshold.

## Final input theorem

A future post-#12565 / post-row-shed consumer may use this donor only when its input
package exact-type satisfies:

- `r04_sale_window is False`;
- `r04_sale_horizon` is a positive non-bool integer;
- `r04_sale_fertilizer is True`;
- `r04_cattle_early is False` (current S32/S33/S34 assembly direction; re-review if the
  final field disposition changes);
- `r04_strawberry_topup is True` (H4);
- `r04_no_late_sale_advance is True` and
  `r04_no_late_sale_advance_step == 648` with exact integer type;
- `r04_b5_carrot_fertilizer is True`;
- `r04_b5_jit_fertilize is True`;
- `r04_row_shed is True`.

The score-facing transform may then set only:

- `r04_sale_window = True`;
- `r04_sale_horizon = 8` (or an explicitly reviewed positive integer override);
- `r04_sale_fertilizer = True`;
- `r04_cattle_early = False`.

Every other configuration key/value and every non-config package byte must survive
unchanged.  `r04_row_shed`, B5/JIT, H4 and L3 are preconditions/preservation witnesses,
not transform-owned values.

## Authority boundary

This donor is deliberately not wired into `make_submission.py`, `apply_v3.py`, package
metadata, defaults, provider code, Kaggle, or any workflow.  It has no submission or
merge authority.  Once #12565 reaches its literal final L3 head and the reviewed
#12551-semantics row-shed consumer is composed with the final cattle disposition, the
**same last-stage #12505 transform lineage** should consume this exact theorem and run
its package-only-diff proof on the literal assembled package.  Do not create a sibling
submission architecture from this analysis module.
