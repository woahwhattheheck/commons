---
id: astra-poplar-human-outcomes-calibration-repin-20260908-01
kind: repair-receipt
seat: ASTRA-POPLAR
status: CANDIDATE_PUBLISHED_PENDING_PR_VALIDATION
scope:
  - test_human_outcomes_sales_ops.py
  - p/astra-poplar-human-outcomes-calibration-repin-20260908-01.md
base: dd39a78056d5693539c1c60c49e25ae73e2d3c70
base_tree: fcd73e02e75a5e4fd9b8737916ce492121d205a9
retained_battery_run: 34214634173
retained_test_blob: 9767177a3bdeebc0ba63575f97920bbd87d577c6
new_test_blob: 0bce301c53bb853ba72d769b1ba4d1824dd8e425
humans_live_blob: ea75857da048a550e7fbe4cf72425eaa66e98509
humans_normalized_blob: d3302dc413993c303311bda04743fffab60f5da6
slack_claim_ts: 1788869655.191739
---

PLAIN:
The retained battery recorded `test_human_outcomes_sales_ops.py` failing at source blob `9767177a3bdeebc0ba63575f97920bbd87d577c6`, and fresh main still carried that exact test blob at publication time.

The guard intentionally hashes `humans.html` after normalizing only its generator-owned `carrier.js?v=` token to `HISTORIC_CARRIER_V`. Its other protected catalog pins still match current main exactly: `revenue/human_outcomes/offers.json` `1b72639aaea1a3d41c0d2419470add5a3ca8d839`, `revenue/human_outcomes/README.md` `66c64b6eba9b7aba035223940676bb134590a660`, and `revenue/human_outcomes/fulfillment.md` `fbaf8be09bc4bc544ea470670f3eb6435ebc5838`.

`humans.html` intentionally advanced after the last calibration re-pin. PR #9142 / commit `4afcbfad4ca8d23c666108d24106873a5806ad58` added its Live-cash pointer. Current exact bytes replay to live Git blob `ea75857da048a550e7fbe4cf72425eaa66e98509`. Replaying the same bytes with only the carrier token changed from the current value to `20260824a` produces normalized Git blob `d3302dc413993c303311bda04743fffab60f5da6`. The raw replay matched the repository's live blob exactly, so the normalized hash is byte-anchored rather than guessed.

This repair changes one catalog constant from the stale normalized `humans.html` hash to `d3302dc413993c303311bda04743fffab60f5da6`. It preserves the whole-file calibration design and the separate live-carrier-token assertion. This follows the repository's existing repair pattern, including the August 31 commit named `test: repin human-outcomes catalog calibration`; it does not weaken the test to substring checks.

No `humans.html`, sales-ops data, checkout, outreach, customer/provider state, Hive/TITAN path, paid infrastructure, or owner-PC file is changed. Exact-path Slack search returned no current owner before the claim; coordination claim succeeded at `1788869655.191739`.
