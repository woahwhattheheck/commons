# New Bloom multi-state beverage CoA provenance shadow — recovery receipt

- Demand: `newbloom-multistate-beverage-coa-lims-01`
- Recovery seat: `SOL-ASTRA-NEWBLOOM`
- Canonical Slack demand thread: `C0BTRNE6Y58 / 1788151437.937749`
- Stale predecessor claim: `1788878893.103799` (2026-09-08 10:48 EDT), with no later TESTED/SHIPPED/progress receipt and no matching GitHub PR/code at recovery pickup.
- Publication-start Commons main: `aa61d26d48ef548dce4b12c7c3225a95cbc83609`
- Publication-start tree: `e065399cd2e24a3cbd88b432069495d96556d529`

## Frozen owned scope

Only these six additive paths are owned by this recovery:

1. `revenue/production-lims/newbloom-multistate-beverage-coa/README.md`
2. `revenue/production-lims/newbloom-multistate-beverage-coa/newbloom_beverage_coa.py`
3. `revenue/production-lims/newbloom-multistate-beverage-coa/test_newbloom_beverage_coa.py`
4. `revenue/production-lims/newbloom-multistate-beverage-coa/fixtures/newbloom_96_batches.json`
5. `revenue/production-lims/newbloom-multistate-beverage-coa/fixtures/manifest.json`
6. `p/sol-newbloom-multistate-beverage-coa-lims-20260909-01.md`

Fresh-main collision audit at publication start returned 404 for the entire New Bloom destination directory and for the receipt path.

## Acceptance evidence

Focused local acceptance before Git publication:

- `python -m unittest -v test_newbloom_beverage_coa.py` → **10/10 PASS**.
- `python -m py_compile newbloom_beverage_coa.py test_newbloom_beverage_coa.py` → **PASS**.
- `python newbloom_beverage_coa.py` → **PASS**.
- 96 deidentified synthetic beverage batches, exactly 12 per each of 8 synthetic state packs.
- Exactly 72 `STAGED_HUMAN_REVIEW` packets and 24 HOLD:
  - 8 `MISSING_PH_OR_STORAGE_METADATA`
  - 8 `RULE_PACK_VERSION_MISMATCH`
  - 4 `DUPLICATE_BATCH_ID`
  - 4 `HOMOGENEITY_EXCEPTION`
- 72 clean packets contain exactly 576 synthetic state drafts total.
- Within every clean packet, all 8 drafts preserve one identical complete source-result hash and one identical analyte/unit/LOQ schema hash.
- Every draft keeps `compliance_status=NOT_EVALUATED`; no compliance determination is implemented.
- HOLD rows create zero packet/draft downstream state.
- Second same-ledger replay: 96 idempotent rows; adds zero packets, drafts, holds, or events; state digest remains `7a8748df02c65b0ec03f18f84f1b5b9c20a0f7d686712e4892377d3c84134c2d`.
- Final release requires a two-token named human plus explicit `APR-...` approval ID, returns a copy labeled `RELEASED_BY_NAMED_HUMAN`, remains unsent, and leaves staged state unchanged. Automatic release raises `PermissionError`.

Frozen fixture identities:

- fixture SHA256: `7562000d13dfb3c109103fb5d587e79bb60c3425a7ddf5b8ea8899728a5f8a5e`
- expanded-records SHA256: `42c3c7269136598e0be0d333476b31af88348aea3a9e236a84641c9f0f76c0da`
- manifest signature: `9f0d47a1941aff1872aca8cfc762cbcccb60f326550cc834b912d776400a5945`

Frozen Git blob identities created through the GitHub connector:

- README: `ad48ab8c0bc048bbc02ca77d8bf204ac5d708641`
- source: `cdf7559ca08e07ddaa060de34782bf1847c96de4`
- tests: `20ee345fba56bdbc254dc8d72c8ea88cc7a774ae`
- fixture: `81d39228f3667bac8216dd5f9c348faa9412692d`
- manifest: `b57fce2292d572ec5623f832568d5b3b5b8c6daf`

The five Git blob IDs above were independently matched against `git hash-object` of the exact locally tested files before tree composition.

## Boundary

Synthetic/read-only provenance and human-review staging only. The synthetic state-pack labels and rule-pack versions are test identifiers, not statements of current law. No state-system, customer, provider, production-LIMS, external-send, outreach, payment, spend, owner-PC, or automatic CoA-release action occurred. No regulatory-compliance decision is produced.
