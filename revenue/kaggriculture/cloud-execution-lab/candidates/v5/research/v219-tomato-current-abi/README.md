# V219 tomato investment — current ABI recovery

This package recovers the **base V219 finite tomato investment** that was always present inside the submitted V3.1 R03/R04 policy family. It is not the later `v219-fertcap` ablation, which was separately tested and rejected.

## Score authority

- submitted V3.1 source tree: `a90d888f03987ef0b35cfd20ec3519c6144db08a`
- submitted V3.1 archive SHA-256: `5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361`
- donor: `candidates/v3/overlay/r04_full_router.py`, V219 layer before V224/V226/V231/V233/E184
- current-V5 parent at carrier creation: `6e3c74b091361445c4429e7501cd5ab0cfd75b52`

The donor's V219 theorem is a bounded day-18..29 investment: qualify from public state, buy SE land + 10 tomato seed, add bounded daily labor/fertilizer purchases, confirm new workers from observations, plant/water/fertilize/harvest, return cargo, and request only physically available tomato sales.

## Current-native timing adaptation

The submitted R03 family had already fixed the route family when V219 qualified at step 432. Current Arlene still owns a public route decision at step 433 (`inv_MILK` can switch to the `MILK_GLUT` continuation). A step-432 route authority can therefore become stale one callback later.

This carrier intentionally qualifies at **step 433**, after that current-native route choice has committed. V219's donor request window allows day-18 offsets through hour 3, so hour 1 remains inside the finite investment window. This is a current-ABI timing adaptation and must be judged by matched economics; it is not claimed as callback-for-callback donor parity.

## One committed-route authority

No feature-local route oracle is introduced. Runtime composition must use the already-landed shared `research/current-route-witness/current_route_witness.py` **v2** seam. The caller supplies the route identity from the committed producer/entrypoint receipt; the shared witness authenticates `controller.R[completed_route_id]` and deliberately ignores raw `controller.cur`. The composer may detach that exact committed route value and pass its witness `route_sha256`; `v219_current.py` canonicalizes and re-hashes the detached full route and fails closed unless it matches. After qualification, any route digest drift disables further V219 work.

## Retry-safe composition entrypoint

`v219_current.py` is the donor-port core. **`v219_current_safe.py` is the composition entrypoint.** The wrapper adds no gameplay theorem: it fingerprints the exact observation, selected action, configuration, enablement, full committed-route snapshot, and route SHA. An identical repeated callback at the same step replays the previously computed V219 action byte-for-byte without consuming pending state twice; any same-step input conflict fails closed to the current selected action while preserving state. This is required because the current harness can retry a callback after state from a completed return has been retained.

## Safety and composition boundary

- selected-action transform only; never calls a controller or producer
- literal `enabled is True`; default-OFF research component
- strict standard engine configuration only
- copy-on-write selected action and state
- exact donor public eligibility gates retained, with committed-route conflict checks through days 18..29
- same-step retry idempotence lives only in the thin safety wrapper
- no runtime/default/config/composition/archive/release/Kaggle activation in this carrier
- activation requires a single V5 composition, natural engagement evidence, and matched both-seat economics against the exact V3.1/V4 authorities

## Authored contracts

After the retry-safety correction, connector-local authored controls are:

- `python -m unittest -v test_v219_current.py test_v219_retry_safe.py`: **17/17 PASS**
- `python -O -m unittest -v test_v219_current.py test_v219_retry_safe.py`: **17/17 PASS**
- normal and optimized `py_compile` across core, safety wrapper, and both test modules: PASS

Those are authored-local receipts, not merge authority. Before merge, the exact GitHub head must receive hosted normal + `-O` + compile receipts, remain additive-only relative to current main, and rejoin fresh moving main without widening scope.
