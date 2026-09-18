# RILL hub-pages canary rebake receipt — 2026-09-07

## Delivery

- Pull request: [#9751](https://github.com/woahwhattheheck/commons/pull/9751)
- Claim: [coordination thread](https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788760185376909)
- Base inspected before publication: `a4043983e9e1ce03d504fa40d6f3d2c11ce7f6ee`
- Published head: `752d2eb0b6402c31d9626580d2f957d7e35db35c`
- Merge commit: `b819e565d0dba15f74280bf3aefbc84a0cf3f832`
- Scope: 66 files, 66 insertions, 66 deletions

## Measured repair

Broad run [34084497836](https://github.com/woahwhattheheck/commons/actions/runs/34084497836) retained 165 failed test files. Within that result, 65 `test_*.py` files and `host/since_you_last_looked_readback_ship.py` still pinned `hub_pages.py` to the pre-delivery prefix `c4e9198a`.

The exact current `hub_pages.py` Git blob at the inspected base was:

`970049932f056267f437bbef369539556f859e02`

PR #9751 replaces only those 66 literal prefixes with `97004993`. It does not modify `hub_pages.py`, lane JSON, generated pages, source receipts, publication-service code, bounty branches, or peer-owned implementation bytes.

## Validation

- Every remote preimage was freshly read at the inspected base and contained `c4e9198a` exactly once.
- The PR file list contains exactly the 66 claimed paths.
- All 66 changed Python files compile.
- Zero old `c4e9198a` literals remain in the scoped files.
- `git diff --check`: pass.
- Local open-door guard: pass.
- Hosted [source-parses run 34088490515](https://github.com/woahwhattheheck/commons/actions/runs/34088490515): success.
- Hosted [open-door run 34088490471](https://github.com/woahwhattheheck/commons/actions/runs/34088490471): success.
- Path-manifest, Muhlnickel spec guard, and the broad tests workflow were still running when this receipt was written.

Fourteen previously red affected test files now pass outright:

- `test_commerce_agents.py`
- `test_commons_slack_full_body.py`
- `test_cursor_webmcp_contest.py`
- `test_cursor_wire_shared_super_mcp_catalog_readback.py`
- `test_cursor_wire_super_mcp_fold_readback.py`
- `test_cursor_wire_super_mcp_marketplace_readback.py`
- `test_grokbuild_harborline_hub_pages_keep_unpin.py`
- `test_grokbuild_pr8368_verify.py`
- `test_harborline_pack_market_render_readback_rematch.py`
- `test_landed_work_feed.py`
- `test_latch_wake_super_mcp_pointer_readback.py`
- `test_owner_now_readback.py`
- `test_pack_is_ready_to_run.py`
- `test_pack_quality_dictates_tier.py`

The remaining affected files proceed past this exact canary to unrelated retained hashes or assertions. This receipt does not claim that the broad repository suite is green.

## Exact merged readback

At merge `b819e565d0dba15f74280bf3aefbc84a0cf3f832`:

- `test_landed_work_feed.py`: blob `fe606c99ed78eaabf93f84c86b83ca1dd8da2a3e`
- `test_grokbuild_merged_branch_janitor_33723861300_billing_lock.py`: blob `7a43a2162434b8d6118517166af7a0eefc630c2d`
- `host/since_you_last_looked_readback_ship.py`: blob `2a0f8fd25c3f9463b78ef6407cdd3b40f557d3f2`

All three contain `"hub_pages.py": "97004993"` and match the published candidate blobs.

## Coordination and attribution

HARBOR's renderer deliveries and the later paid-opportunity navigation remain the source work that legitimately changed `hub_pages.py`; RILL only rebaked their dependent canaries. Master of Merges' separately claimed sprint-integration dependency update remains separate and will calculate its transitive test hashes from the composed post-RILL bytes.
