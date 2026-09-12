# V219 tomato investment — current ABI recovery

This package recovers the **base V219 finite tomato investment** that was always present inside the submitted V3.1 R03/R04 policy family. It is not the later `v219-fertcap` ablation, which was separately tested and rejected.

## Score authority

- submitted V3.1 source tree: `a90d888f03987ef0b35cfd20ec3519c6144db08a`
- submitted V3.1 archive SHA-256: `5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361`
- donor: `candidates/v3/overlay/r04_full_router.py`, V219 layer before V224/V226/V231/V233/E184

The donor's V219 theorem is a bounded day-18..29 investment: qualify from public state, buy SE land + 10 tomato seed, add bounded daily labor/fertilizer purchases, confirm new workers from observations, plant/water/fertilize/harvest, return cargo, and request only physically available tomato sales.

## Current-native timing adaptation

The submitted R03 family had already fixed the route family when V219 qualified at step 432. Current Arlene still owns a public route decision at step 433 (`inv_MILK` can switch to the `MILK_GLUT` continuation). A step-432 route authority can therefore become stale one callback later.

This carrier intentionally qualifies at **step 433**, after that current-native route choice has committed. V219's donor request window allows day-18 offsets through hour 3, so hour 1 remains inside the finite investment window. This is a current-ABI timing adaptation and must be judged by matched economics; it is not claimed as callback-for-callback donor parity.

## One receipt-bound committed-route authority

No feature-local route oracle is introduced. Runtime composition consumes the landed shared `research/current-route-witness/current_route_witness.py` **v3** authority. The public V219 adapter accepts the immutable current callback receipt `{route_step,last_step,player,route}`, not a caller-selected route id. It uses the shared witness validator to require the receipt's route step and last step to equal the current observation step and its player to equal the current observation player. Only then does it capture `controller.R[receipt.route]`; raw `controller.cur` is deliberately ignored.

The detached full route is canonicalized and re-hashed again by `v219_current.py`. Any malformed/stale/carried/cross-player receipt, unknown route, route digest mismatch, or later route drift fails closed before V219 may change the selected action. Receipt fields, the complete captured route, and its digest are included in the retry key, so a different producer authority cannot reuse an earlier same-step result.

## Retry-safe composition entrypoint

`v219_current.py` is the donor-port core. **`v219_current_safe.py` is the composition entrypoint.** The wrapper adds no gameplay theorem: it fingerprints the exact observation, selected action, configuration, enablement, validated current route receipt, full committed-route snapshot, and route SHA. An identical repeated callback at the same step replays the previously computed V219 action byte-for-byte without consuming pending state twice; any same-step input or authority conflict fails closed to the current selected action while preserving state. This is required because the current harness can retry a callback after state from a completed return has been retained.

## Safety and composition boundary

- selected-action transform only; never calls a controller producer or route-selection method
- literal `enabled is True`; default-OFF research component
- strict standard engine configuration only
- copy-on-write selected action and state
- exact donor public eligibility gates retained, with committed-route conflict checks through days 18..29
- same-step retry idempotence lives only in the thin safety wrapper
- no runtime/default/config/composition/archive/release/Kaggle activation in this carrier
- activation requires the one V5 composition, natural engagement evidence, and matched both-seat economics against exact V3.1/V4 authorities

## Verification boundary

The pre-v3 adapter had authored-local normal/optimized/compile receipts. They do **not** authorize this receipt-bound successor. The current exact GitHub head must independently pass the focused normal and `-O` suites plus compilation, remain additive-only relative to fresh main, and preserve this six-path research/CI surface before merge. Gameplay/economic evaluation starts only after that source gate is green.
