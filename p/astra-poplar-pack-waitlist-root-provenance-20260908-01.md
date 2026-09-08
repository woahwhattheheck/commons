---
id: astra-poplar-pack-waitlist-root-provenance-20260908-01
kind: repair-receipt
seat: ASTRA-POPLAR
status: LANDED_TESTED_BYTES_PENDING_MERGE
scope:
  - host/pack_waitlist_pointer.py
  - test_pack_waitlist_pointer_root_provenance.py
base: 2cce66ea760d31a8c6af20c7309f25da3f2242d8
base_tree: 31f3de48f7518cf17290e6433f4584d0359859fb
baseline_source_blob: 0e34246f55cfd2cd5f9ec914cb6fc6a9669a626f
patched_source_blob: 0dac3b61ae41de9bb996ff077ee7e310e41a9ab7
new_test_blob: 7ba9711c9fa2287f411f98a8cdc7d8d745a416fa
---

PLAIN:
`classify(root=...)` previously selected measured files from the supplied checkout while loading the pointer law from the module default checkout. The repair selects `ground/BUSINESS_PACK_WAITLIST_POINTER.json` from the explicit root, while preserving default-root lookup, configured `POINTER_LAW`, explicit dictionary overrides including `{}`, CLI behavior, and the existing read-only/non-gate contract.

Validation in the cloud container used real temporary directory trees. Baseline: 10 of 18 test methods failed or errored. Patched: 18/18 pass, 0 skips. This is a bounded repair and does not claim repository-wide battery closure.

Publication provenance: fresh main was read before Git Data writes; source remained at the retained baseline and the new test path was absent. An earlier manually re-encoded orphan blob produced a mismatched SHA and was discarded before tree creation. Exact tested source/test bytes were then written and matched expected Git blob SHAs above.

Coordination provenance: the actual Slack message writer was invoked for the claim and returned HTTP 429 `ratelimited`; no false Slack claim receipt is asserted here. The delivery message should be retried after merge.

No owner data, historical pack pins, Hive/TITAN paths, customer/provider state, paid infrastructure, or owner-PC files were changed.
