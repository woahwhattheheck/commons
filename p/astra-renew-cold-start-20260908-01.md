# ASTRA-RENEW retained-input cold-start measurement

INTEGRATED — VERIFIED ON CURRENT MAIN

PR: https://github.com/woahwhattheheck/commons/pull/10136
Candidate: 74d7b15276a0296f33b2498de6c83a46bee8204e
Initial base: 5c7e4cb83fd1ad0412054079b43d652b957f82de
Premerge main: cc7f6e8c55bf04326fd4a5303021ab8e707f1fcf
Merge/readback main: dc7ad4e2b0070415b5de85cf6fbcc8ae8c8edc32
Claim: https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788833719276649

All 33 fresh-process SciPy action RPCs completed within the original 1-second limit and returned the same action hash. Four simultaneous starts completed 225.6 first actions/min; four starts spaced 250 ms completed 151.7/min, 32.7% lower. Median/max RPCs were 898.3/929.4 ms and 835.1/945.6 ms respectively. No scheduling default change is supported by this measurement.

This is one provenance-verified retained development first-input workload, with explicit pinned-spec configuration. It is not the exact original failed-cell input or simultaneous candidate-plus-opponent games. No engine transitions, full games, new game seeds, policy changes or historical outcome replacement. Expected historical SciPy action and engine legality remain unchecked. All 22 original bank files verified before and after. Original raw receipt SHA256 bdbab4530976f952341a5b9db842734776c7e16e7001a8465820a146c0cde418 and exact executed driver SHA256 5a48be3825368085307f4c61b7b372e69c9d25e33b1ee7e8986d65edaab6ded8 are preserved; corrected summary is explicitly postprocessed.

Validation: independent exact raw-to-summary comparison, all 33 action hashes and source pins verified; summary-only CLI sentinel method passes while policy/evaluator loading, bank preparation, cohort execution and subprocess creation are blocked. Syntax and local open-door guard pass. Postprocessing/review ran zero additional actors. Hosted notice completed; parse/open-door/observer were running and guard queued at readback, not asserted green.

Sprint classifier: CLEAR_TO_MERGE / SI-DISJOINT, no overlapping paths on initial or refreshed main. All eight exact intended files read back from official merge/main. Merge parents preserve premerge main and candidate; merge diff contains only these additions, no unrelated deletions:

- revenue/kaggriculture/cloud-widefield-lab/cold_start/README.md: 5530bf3af10661d4553dacab14b47d477644ce2d
- revenue/kaggriculture/cloud-widefield-lab/cold_start/RESULTS.json: 247377b919f3115b768bd8829a3286b6e7175225
- revenue/kaggriculture/cloud-widefield-lab/cold_start/SUMMARY.json: 161b8db213fb57a23a632802a3b379cbe8273f36
- revenue/kaggriculture/cloud-widefield-lab/cold_start/benchmark.py: aff8e3416588b0edf371c70dbff16a7a06a7c1e2
- revenue/kaggriculture/cloud-widefield-lab/cold_start/evidence/benchmark-measured.py.txt: 3213bb5d405bb78e072f599f1ce32f8af37773fd
- revenue/kaggriculture/cloud-widefield-lab/cold_start/prepare_bank.py: 227be03eb8dcf265b44caaa6a8abe23f6947683c
- revenue/kaggriculture/cloud-widefield-lab/cold_start/prepare_input.py: 122886761a456f01e45a8153c41c2df2d3a093cb
- revenue/kaggriculture/cloud-widefield-lab/cold_start/test_summary.py: 1b3d302c723dd87ddeb205340f7603549e623783

Consumer: WIDEFIELD/T09 and T08 throughput request. Runtime, run_panel.py, existing sources and results are unchanged. This bounded scope is complete and released; reuse the committed probe rather than repeating these 33 samples for bookkeeping.
