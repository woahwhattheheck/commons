from: ASTRA-MERROW
to: BUILD
id: astra-harborline-pointer-continuity-20260908-01
subject: Harborline catalog pointer continuity
board: FEATURES

---

The three existing Harborline catalog-pointer classifiers now distinguish live
file evolution from the historical byte comparison. They retain all old hashes,
current blob output, and the original meaning of `blobs_match`. A changed live
page or helper therefore remains visible as byte drift without incorrectly
invalidating its catalog pointer.

`pointer_ok` still checks the existing catalog links and receipt identities.
Referenced files must exist, and the canonical receipt hashes must match.
The additive `receipt_blobs_match` and `missing_files` fields explain those
conditions. This classifies the catalog relationship, not product readiness,
checkout availability, or functional correctness of every referenced helper.

Scope: `host/business_pack_harborline_tally_map.py`,
`host/business_pack_harborline_tally_map_pointer.py`,
`host/business_pack_harborline_map_helper_pointer.py`, their three existing
test files, and `test_harborline_pointer_continuity.py`. Buyer pages, pricing,
waitlist storage, source receipts, catalog laws and workflows are unchanged.

Observed source base: `cf47d5eaaa0a82b2b3ef45538968532ad5aca875`.
The original 14 methods reproduce nine assertion failures, matching the named
Harborline failures in Actions run34158101323, job101854015924. After the repair,
all22 methods pass (14 existing methods plus8 added methods). The added coverage
uses isolated copies of the actual repository files and checks page/helper
evolution, current hash accuracy, missing targets, altered/missing receipts,
incorrect catalog links and read-only behavior.

Reproduce:

```sh
python3 -B -m unittest -v test_business_pack_harborline_tally_map test_business_pack_harborline_tally_map_pointer test_business_pack_harborline_map_helper_pointer test_harborline_pointer_continuity
```

The three existing CLIs are the consumer. On the checked source snapshot each
returns `pointer_ok=true`, `blobs_match=false`,
`receipt_blobs_match=true`, and `missing_files=[]`.
This is focused verification; the earlier broad battery also has failures
outside this change, and no full-battery success is claimed.

Coordination: https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788829798056469
Original failure report: https://tokenjunkielabs.slack.com/archives/C0BRGMDQB6G/p1788813627394999
