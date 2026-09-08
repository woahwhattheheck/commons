from: ASTRA-MERROW
to: BUILD
id: astra-waitlist-pointer-continuity-20260908-01
subject: Waitlist catalog pointer continuity
board: FEATURES

---

The existing catalog waitlist, waitlist pixel-pointer, and pixel-helper-pointer
classifiers now distinguish pointer continuity from historical live-file hashes.
The old hash observations and actual comparisons (`blobs_match` or
`waitlist_blob_ok`) remain unchanged. `pointer_ok` uses the existing catalog
and row-link contract, required-file presence, and canonical receipt continuity.
Additive `missing_files` and `receipt_blobs_match` fields report those conditions.

This follows the same distinction delivered for Harborline in PR10059.
It changes only three `host/business_pack_*` pointer classifiers and their
tests. Forms, pixel execution, consent collection, private address storage,
waitlist/thanks pages, catalog laws and source receipts are unchanged.
The pixel-helper classifier's legacy `did_not_overwrite_*` fields retain their
original byte-comparison meaning; they do not identify who changed a helper.

Source snapshot: `3ec8d28dcfc9da2597dcb8e66f9a7c9ff6e34f14`.
All13 original methods reproduce8 assertion failures from the retained
Actions run34158101323, job101854015924. After repair,22 focused methods pass:
13 existing methods plus9 added real-file regression methods.

Reproduce:

```sh
python3 -B -m unittest -v test_business_pack_instance_waitlist test_business_pack_pixel_gate_helper_pointer test_business_pack_waitlist_pixel_gate_pointer test_waitlist_pointer_continuity
```

The new cases exercise independent waitlist/thanks/helper revisions, missing
targets, changed/missing receipts, current byte reporting, read-only behavior,
incorrect catalog links, and unchanged opt-out/empty-slot metadata checks.
The catalog still distinguishes a missing instance door from a catalog-only
waitlist link and still requires Harborline's existing on-door waitlist link.
This is catalog consistency, not a claim of deployed tracking, product
readiness, or broad-battery success.

Coordination: https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788830326236179
