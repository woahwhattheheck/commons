# V5 V3.1 fertilizer-hand current-ABI recovery

This directory recovers one measured V3.1 theorem without reviving the V3/R04 controller.

## Historical authority

The submitted V3.1 source is commit `a90d888f03987ef0b35cfd20ec3519c6144db08a`. Its `candidates/v3/overlay/r04_fert_hand.py` blob is `79fefde712a38f802e9d77e68b3f8943fe137cd3`; the submitted archive is SHA-256 `5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361`.

The historical fleet receipt reported the endgame fertilizer-hand mechanism at +261.6 cash/game across 1,920 field games, with 853 better cells and zero worse cells. That is historical evidence only; it is not a current-V5 promotion receipt.

## Current-ABI theorem

The useful invariant is parent isolation, not the legacy wrapper:

1. after a candidate HIRE is observed as one additional hand, remove exactly that owned hand and its matching private inventory from the observation before the existing producer runs;
2. leave the producer's farmer, incumbent-hand and market decisions untouched;
3. after selection, reinsert only the owned hand's action at the exact hidden index;
4. reserve future authored HIRE and FERTILIZER pickup intent from a complete same-day route tail before admitting the extra hand or consuming fertilizer;
5. reproduce the same candidate decision on unchanged same-step retries, but retire a cached candidate HIRE if refreshed current/future parent authority now contains HIRE;
6. drop ownership on day rollover/cardinality ambiguity.

`fert_hand_current.py` contains the recovered base theorem. **The public consumption surface is `fert_hand_current_safe.FertHandCurrentABI`**, which adds refreshed-parent retry revalidation and permanent fail-closed retirement of a conflicting cached HIRE. New consumers must import the public class from `fert_hand_current_safe`, not instantiate the base class directly.

Neither module calls a producer, edits `titan_runtime.py`, flips a config/default, builds an archive, or alters Kaggle state.

## Admission

The candidate retains the V3.1 economic shape: days 24-28, no parent HIRE now or later that day, exact Fibonacci daily HIRE cost, CARROT fertilizer yield opportunity, explicit fertilizer acquisition cost, market-prefix capacity, and a positive gain floor/ratio. Standard Kaggriculture geometry/timing is fail-closed.

Before any production activation, this source needs a fresh current-V5 matched evaluation with both seats and competitive opponents. Promotion must use the V5 promotion gate and current release-pointer authority; the historical V3.1 result is only the reason to test this port.

## Focused checks

Run from this directory:

```bash
python -B -m unittest -v test_fert_hand_current.py test_fert_hand_retry_safe.py
python -O -B -m unittest -v test_fert_hand_current.py test_fert_hand_retry_safe.py
python -B -m py_compile fert_hand_current.py fert_hand_current_safe.py test_fert_hand_current.py test_fert_hand_retry_safe.py
```

The tests bind submitted-V3.1 provenance, engine HIRE-cost parity, exact parent-view removal/reinsertion, clean same-step retry stability, refreshed current/future HIRE retirement with no resurrection, malformed retry fail-close, market preservation, complete-route-tail gating, collision/capacity rejection, strict public identity/configuration, cardinality fail-close, and day-reset ownership.
