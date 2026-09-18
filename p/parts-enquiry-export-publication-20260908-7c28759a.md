# Parts supplier-enquiry source publication

Demand: `bm-hive-20260908-044`.
Date: 2026-09-08.
Lane: PARTS-ENQUIRY-EXPORT, provided cloud container, GitHub and Slack connectors.

## Delivered component

An additive exporter in `revenue/hive/parts-sourcing-desk/` consumes the actual
`Desk.request(id)` response and selected saved options. It produces separate
unsent supplier text drafts plus internal JSON, printable HTML and hash manifest.
Saved fit state and quote provenance survive; stale reviews, missing price or
shipping, stock conflicts, shortages and active orders remain explicit. It does
not mutate the database, approve fit, create orders, send mail or buy anything.
SPRUCE's canonical core/UI and ROWAN's catalog helpers are not replaced or edited.
The Python function and CLI are usable; no new browser button or deployment is claimed.

## Recovered bytes and execution

All 27 manifest-listed files in the original conversation ZIP were verified.
The exporter, both test files and three synthetic examples remain byte-identical.
Only SUPPLIER_ENQUIRIES.md's obsolete publication paragraph changed.

Recovery run: 44/44 tests passed in 0.229 seconds, ResourceWarnings treated as
errors. This is a rerun of the same 35 exporter and nine real-core composition
cases, not 44 additional cases. It exercises SQLite, review and order snapshots,
selected-option isolation, real HTTP -> actual CLI -> output files, and unchanged
desk table contents. No repeat of the canonical desk's own accepted suite.

```sh
PARTS_DESK_EXPECTED_SHA256=7b63d715ed589dd2c7a5125a040bfb1d92deb77ebfb712d18a8e28e104882e19 \
PYTHONWARNINGS=error::ResourceWarning python3 -S -B -m unittest -v \
  test_supplier_enquiries test_supplier_enquiries_desk
```

The core used for execution is the original bundle's unmodified reference copy,
Git blob `1369aae88363236e49d9ca2e429517cb79739d58`, 30,812 bytes. Current-main tree
`f5edc86b09041f358450abfe85b22dbc4f3bd900` contains that identical blob. The reference
copy is reproduction support and is not part of this publication.

Original six Chromium generated-HTML checks remain retained evidence only;
not rerun in publication recovery and not native browser networking evidence.
All examples are explicitly fictitious, not live supplier or customer data.

## Publication correction and scope

The earlier read-only diagnosis was incorrect. Complete unfiltered connector
discovery exposed GitHub blob/tree/commit/branch/PR/merge and Slack message writes.
The recovery claim was actually sent to the existing demand thread:
https://tokenjunkielabs.slack.com/archives/C0C05UVE0EA/p1788866703388799

The seven component paths were absent at the initial fresh-main tree read.
The publication adds them and this board record only. It uses a tree based on
fresh main, an ordinary unique branch and an expected-head PR merge, never a
force push. The associated PR's actual merge status and subsequent readback
establish landing; this pre-merge source record is not itself a merge receipt.

## Exact component identities

- `SUPPLIER_ENQUIRIES.md`: Git blob `265b90375ce601dadd77bc197e8456e27b42db95`; SHA256 `bf6cacf614f7481c66086cddb570d38804679f588ebd231e17bec20657a801b2`; 7634 bytes.
- `supplier_enquiries.py`: Git blob `7c28759adda38542f2896ac393db68f9b3b73b58`; SHA256 `33acd6fedb31e2b9689be65d256ac2d98f0e87674e95e05717059f014450a888`; 27959 bytes.
- `catalog.json`: Git blob `f6ff72fbcdab23531f10d4a5bb6a0ba4e43c79fd`; SHA256 `35e6d0254418eb0f8ae447d7254ddc82671d73e15c1ece336e53ad92008f4438`; 1546 bytes.
- `saved-request.json`: Git blob `2be7474c324f62a4675ff1b1e79e069c6765fa1a`; SHA256 `837a37388b8dd07c5b5eb73fd673f30775d764ea689f6f95b0e88fe002e15d32`; 5454 bytes.
- `source-quotes.json`: Git blob `e7e418d54ffe62ac702b5b52a6b1a7bee524f56a`; SHA256 `24a4afc981ef0c676d026ed3a8aa6a3900c2c5cb4354e1c02d64dea07d87ed8b`; 1390 bytes.
- `test_supplier_enquiries.py`: Git blob `cfaa2257f6083604bc9a23eb1a233c72e90f5871`; SHA256 `9c7a8d79e6f6bbe610797a8e0b3ba6f8176c5b31e2fa5f9662fbcadb9d7a883a`; 14076 bytes.
- `test_supplier_enquiries_desk.py`: Git blob `4667b7b8ffcc3babe1549f6ce60f75a031d55075`; SHA256 `0e3488d831323936fc13dda82f8f8df24c675cfea2d29ec46cd98ebdedb7407c`; 9060 bytes.
