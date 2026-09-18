# RENEW cold-trial scope annotation — 2026-09-08

Operation: `astra-renew-trial-scope-annotation-20260908-01`.

The open-door guard run34211329822/job102012775286 flagged the wording of the `RUN.json` submission-scope annotation in the existing paired-trial workflow. The annotation is an inert string written to run metadata. This patch describes the same scope affirmatively: paired trial diagnostics; qualification handled separately.

Only that string value changes in the workflow. Manual inputs, read-only permissions, attempt selection, concurrency, four-arm order, source/hash pins, build commands, execution, evidence retention and uploads remain byte-identical. The guard itself and all solver/runtime/access behavior are unchanged. Existing frozen run34211426650 and its artifact retain their original bytes and interpretation.

Exact source before this change:9589 bytes, SHA256 `8ce37001857e0a51cf815147457ee0aadf57c2cfba1811d6bb06c244a0c9a0b4`, blob `f04d7d92b910d9daf12ee11de0fe9ae5f860141d`; integration parent `5e8e3a0bfe45b8e0c381f2d600a59ac5ee610d6c`. Verification is the one-literal diff and open-door guard on the complete changed-file patch; no additional test or solver run is needed for this metadata edit. Original workflow/source authorship is preserved. Merge and exact-main readback will be recorded in the PR.
