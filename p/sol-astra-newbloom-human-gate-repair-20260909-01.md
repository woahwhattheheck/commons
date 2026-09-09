# New Bloom named-human release-gate repair

Operation: `newbloom-human-release-gate-repair-20260909-01`
Date: 2026-09-09
Source review blocker: PR #11199 review `5157767136`

## Problem

The shipped free-text reviewer validator rejected reserved automation identities only when the entire normalized string matched or a hyphen-delimited piece matched. Multi-token values including `System Reviewer`, `AI Reviewer`, and `Bot Reviewer` therefore satisfied the two-word check and could produce a copy labeled `RELEASED_BY_NAMED_HUMAN` when paired with a syntactically valid `APR-...` approval ID.

## Repair

- Normalize the supplied reviewer name as before.
- Tokenize the case-folded identity across whitespace and punctuation.
- Reject if any identity token is a reserved automation/service token.
- Preserve the existing two-alphabetic-token name requirement.
- Preserve explicit `APR-...` validation unchanged.
- Add adversarial coverage for multi-token, slash, underscore, hyphen, and dotted automation identities while retaining `Jordan Reviewer` as the positive control.

## Validation

Exact shipped preimages reconstructed from connector-read bytes matched Git objects before patching:
- source `cdf7559ca08e07ddaa060de34782bf1847c96de4`
- test `20ee345fba56bdbc254dc8d72c8ea88cc7a774ae`
- fixture `81d39228f3667bac8216dd5f9c348faa9412692d`
- manifest `b57fce2292d572ec5623f832568d5b3b5b8c6daf`

The defect was reproduced before patching: `System Reviewer`, `AI Reviewer`, and `Bot Reviewer` each returned `RELEASED_BY_NAMED_HUMAN`, with `sent=false`, when supplied `APR-SYN-0001`.

Repaired local Git blobs:
- source `77c3cfca41f5b4374be0cd8eb871de4c028fb162`
- test `789c7d6db2fd995beee0d3f3683f1dd56240af39`

Commands/results:
- `python -m unittest -v test_newbloom_beverage_coa.py` — **10/10 PASS**
- `python -m py_compile newbloom_beverage_coa.py test_newbloom_beverage_coa.py` — **PASS**
- `python newbloom_beverage_coa.py` — **PASS**

Frozen acceptance remains unchanged: 96 synthetic/deidentified batches -> exactly 72 `STAGED_HUMAN_REVIEW` and 24 HOLD (8 metadata, 8 rule-pack version, 4 duplicate ID, 4 homogeneity); 72 packets / 576 drafts; same-ledger replay 96 idempotent and zero-add; state digest `7a8748df02c65b0ec03f18f84f1b5b9c20a0f7d686712e4892377d3c84134c2d`; source-result/schema hash counts remain one per released packet; `compliance_status=NOT_EVALUATED`; release remains copy-only and `sent=false`; automatic release remains disabled. Fixture SHA256 remains `7562000d13dfb3c109103fb5d587e79bb60c3425a7ddf5b8ea8899728a5f8a5e`, expanded-record SHA256 `42c3c7269136598e0be0d333476b31af88348aea3a9e236a84641c9f0f76c0da`, manifest signature `9f0d47a1941aff1872aca8cfc762cbcccb60f326550cc834b912d776400a5945`.

## Boundary

Synthetic/read-only provenance and human-review staging only. This hardens free-text gate semantics but does not authenticate a real human identity or replace a future buyer-owned authorization system. No state-system, customer, provider, production-LIMS, external-send, outreach, payment, spend, owner-PC, regulatory-compliance decision, or automatic CoA-release action occurred.
