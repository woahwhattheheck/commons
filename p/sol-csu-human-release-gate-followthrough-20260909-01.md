# CSU named-human release gate follow-through — repair receipt

Operation: `csu-human-release-gate-followthrough-20260909-01`
Source task: `csu-malt-method-expansion-lims-01`
Source repair PR: `#11220`
Independent review consumed: `5157858710`
Slack claim: `C0BU51F1PL3 / 1788975725.378869`

## Scope

Only:
- modified `revenue/production-lims/csu-malt-method-expansion/csu_malt_expansion.py`
- modified `revenue/production-lims/csu-malt-method-expansion/test_csu_malt_expansion.py`
- this new receipt

No fixture, manifest, provider, customer, outreach, compliance decision, real record, production system, spend, TITAN gameplay, owner-PC, force-push, or history-rewrite action.

## Fresh-main preimage

Publication base: `169f6147baa149ac4a5aac1a6aa02e3b47ce88b0`
Base tree: `67a8fb1b178ada88713744f86f930dbf9ae2ad6f`
Source preimage Git blob: `dd02ee95fe2a5211aa810975b1e77cf6a0f1aaae`
Test preimage Git blob: `193cc0be3b49859fd4f592381d933e510d1ccac8`

The owned preimages were re-read after concurrent main advanced from `655c85cb5843952fde68f85f3e4024bd9080a3f3`; both remained unchanged before publication.

## Reproduced blocker

`release()` only coerced/stripped the reviewer and rejected an empty value. Any other nonempty string — including `system`, `System Reviewer`, `AI Reviewer`, `Service Account`, and bot/agent variants — could therefore be copied out as `RELEASED_BY_NAMED_HUMAN`. The focused regression rejected only blank input.

## Repair

- Require a string containing at least two alphabetic name tokens.
- Case-fold and split on non-letter separators, so whitespace, punctuation, underscores, hyphens, and digit suffixes cannot hide reserved automation/service tokens.
- Reject reserved tokens `ai`, `agent`, `auto`, `automated`, `automation`, `bot`, `robot`, `service`, and `system` wherever they appear.
- Preserve ordinary named-human examples (`QA Reviewer`, `Jordan Smith`, `Anne-Marie Jones`).
- Preserve the existing copy-only release boundary: both denied and accepted release calls leave the staged ledger report unchanged.

## Acceptance

Executed against the exact candidate source/test bytes with the repository fixture and manifest:

- `python3 -m py_compile csu_malt_expansion.py test_csu_malt_expansion.py` — PASS.
- `python3 test_csu_malt_expansion.py -v` — **13/13 PASS**, zero failures/errors.
- `python3 csu_malt_expansion.py` — PASS with frozen behavior unchanged: 80 processed; 60 `CURRENT_WEEK`; 8 `NEXT_WEEK`; 4 `DUPLICATE_ID`; 4 `UNSUPPORTED_GRAIN_METHOD`; 4 `MISSING_IDENTITY_PACKAGE`; 68 accessions; 130 jobs; 66 staged reports; 12 holds; 80 events; exactly 6 third-party `ASBC-PROTEIN` jobs; replay delta zero.

Candidate Git blobs:
- source `3a8c77fa3450fc0e8f229f725b758fbb0d43c81d`
- tests `836786aa4ae6c3fa6898dbd4517a9d38b5aecf0e`

No production or external action is claimed by this repair.
