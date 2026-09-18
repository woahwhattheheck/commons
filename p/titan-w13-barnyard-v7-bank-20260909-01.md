# TITAN W13 Barnyard V7 bank receipt

Operation: `titan-frontier-W13-barnyard-v7-bank-20260909-01`

W13 asked for additional real reacting public opponents, with author/version/runtime/license binding, policy-preserving wrappers and official-engine compatibility evidence. The external search found stronger/newer leads (notably Kaito V48), but this cloud session had no direct Kaggle artifact transport. COK's newer public controller was rejected because its own notice did not license the independently written controller, and unlicensed public repositories were not vendored.

The shipped unit instead promotes an already-reviewed, redistribution-ready source that was not in either the legacy six-opponent runnable bank or S11: Roman Rozen's Barnyard Economist V7. Its exact policy source is reused by Git blob identity from `revenue/kaggriculture/cloud-opponent-frontier/runtime/barnyard-v7/main.py` and remains SHA-256 `997e6bfc5234534e246e945bc61c87858ebf997ab85b0a5c9427dd4ed710f1b6` / 27,244 bytes. LICENSE, NOTICE and SOURCE receipt are also reused byte-for-byte.

New code is limited to a hash-verifying compatibility adapter and focused tests. `make_agent()` executes a fresh namespace for actor/game isolation; `agent(observation, configuration=None)` exposes the evaluator-friendly signature while intentionally slicing configuration because the upstream policy accepts only `obs`. No policy action or branch is changed.

Exact-source official-engine evidence is preserved rather than overstated: T07 ran 32 primary games under `Kaggle/kaggle-environments@28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`, both seats, 719 decisions/game, zero Barnyard runtime failures. W13 did not execute a new engine match because that pinned engine package is not available in this VM. Existing results also show all 16 Barnyard candidate-vs-Arlene/Apex primary games were losses; therefore this bank entry is research/diversity coverage, not a strength or leaderboard claim.

Local prepublication validation in this session: `python -m py_compile adapter.py test_adapter.py` PASS. The focused runtime regression is committed to run where the preserved source tree is present; repository CI status is reported separately and is never inferred from local syntax validation.

No TITAN strategy/runtime/current-pointer/archive source, replay tape, Kaggle submission, provider state, spending, credentials or owner-PC state is changed.
