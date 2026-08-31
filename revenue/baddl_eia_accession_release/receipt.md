# baddl-eia-accession-release-lims-01 receipt

State: TESTED
Binary: `python3 test_baddl_eia_accession_release.py` → 9/9 OK
CLI: `python3 baddl_eia_accession_release.py` → ok true, failures []

| check | expected | actual |
|---|---|---|
| input rows | 24 | 24 |
| EIA worklist | 22 | 22 |
| intake HOLD | 2 | 2 |
| HOLD codes | HOLD_DUPLICATE_TUBE_ID, HOLD_UNSIGNED_FORM | HOLD_DUPLICATE_TUBE_ID, HOLD_UNSIGNED_FORM |
| negative | 19 | 19 |
| positive | 2 | 2 |
| invalid | 1 | 1 |
| human releasable | 21 | 21 |
| human released | 21 | 21 |
| invalid HOLD | 1 | 1 |
| autonomous released | 0 | 0 |
| replay added accessions | 0 | 0 |
| audit_sha256 | 1849cde855a07b5eef7c389e36c3896bd257161d6d6970292ad17509b55cd204 | 1849cde855a07b5eef7c389e36c3896bd257161d6d6970292ad17509b55cd204 |

Buyer: Florida BADDL / Y. Reddy Bommineni.
Interfaces simulated. No PHI, live animal status, regulatory submission, billing, or automatic result release. AquaTrace HOLD / BUILD-AND-VERIFY. PRE-SALE TRANSPORT: NONE. cash_usd=0.
