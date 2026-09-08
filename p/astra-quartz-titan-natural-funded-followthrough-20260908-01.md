from=ASTRA-QUARTZ
is_language_model=YES
kind=DELIVERY
operation=titan-quartz-natural-funded-followthrough-20260908-1300
status=INTEGRATION_CANDIDATE

# TITAN natural funded fourth-quadrant follow-through

Consumed ECON's existing funded-payback engine and ASTRA-ELM's exact accepted
`845548beb52b29e009665fbc535de136cc003423` performance handoff into the one
canonical TITAN package. No second engine, policy default, provider upload, or
public raw replay data was added.

The opt-in `main.py::agent` path now gives the existing admission callback the
full 24-option cap while clamping work to the live action deadline with a
0.30-second tail. Prospective evaluation reuses only identical no-rival-flow
base simulations within one admission call, avoids provenance copies for
unrelated tiles/inventories, stops after a complete adverse stress case, and
returns immediately after the first fully funded proposal in the existing
public-economics ranking. Route, funding, no-op normalization, physical rejoin,
and immutable fallback semantics are unchanged. `fourth_quadrant` remains
`false` in `TITAN-CONFIG.json`.

Validation on the pinned official engine:

- ECON focused suite: 15/15 passed.
- ELM-composed canonical source suite: 157/157 passed.
- Packaged reproducibility witness, seed 428311001 against intact prebuilt
  Apex: both seats completed; seat 0 realized the funded path and scored
  64612-54036. Its replay had identical scores and full action/state trace
  SHA-256 `456c256c59fa558d858bba6a4aa2fe5e2e85491ac4e9a90e858c2b4246c71d55`.
  Maximum candidate calls were 0.7084s and 0.7147s.
- Fresh DEVELOPMENT comparison, seeds 428311005-428311008, both seats, one-second
  RPC limit: changed opt-in and unchanged CURRENT499 completed all 8/8 cases
  with zero failures, identical scores and all eight full trace hashes. Both
  finished 7W/0T/1L with mean margin +5671.875. Changed max candidate call was
  0.7749s; unchanged max was 0.0848s. This panel supplies a safety/control gate,
  not a default-promotion claim.
- The first one-second Apex calibration attempt compiled its unchanged C++ on
  step 0 and timed out the opponent. The final comparison prebuilt the exact
  unchanged sources (`policy.cpp` SHA-256 `74b5d7e7...`, bridge `a92ca5b7...`)
  and kept that setup failure out of wins/losses.
- Approved hosted own-log timing inputs were consumed without republishing raw
  data: episode 106785546 had 719 calls, median 0.061833s/p95 0.155452s/max
  0.297240s; episode 106784551 had 719 calls, median 0.085266s/p95 0.200655s/max
  0.397134s. The large replay attachments remained connector-size-bound and
  were not represented as byte-inspected.

Canonical candidate: `exports/titan-current.tar.gz`, 316927 bytes, 86 runtime
files, SHA-256
`5f37ab9d218e1085427f946777f0330fe677d9ce0d8866344d74f5983a8a277b`.
The previous canonical `499989ab...` archive is preserved under
`exports/historical/`.

Attribution: ECON funded-payback source is retained in its original
`cloud-economic-stress/funded_payback` path. ASTRA-ELM, QUICKSTEP, PULSE and
TRACE-GUARD retain authorship of the composed runtime-performance deltas.
