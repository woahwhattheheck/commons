# SOL-REVIEW-MVMTC — named-human release gate repair

Demand: `mvmtc-aero-fastener-evidence-lims-01`
Reviewed source PR: #11145, merge `711ef54b9de626cea674aa8b51023e3218d0961b`
Date: 2026-09-09

## Reproduced defect

The landed `release_evidence_pack()` called `reviewer.strip()` directly and rejected only exact whole-string entries in `RESERVED_REVIEWERS`. On current-main bytes this allowed obvious multi-token automation labels such as `System Reviewer`, `AI Reviewer`, and `Bot Reviewer` to release a READY W1-style evidence pack under `RELEASED_HUMAN_REVIEW`. Non-string reviewer values also raised an incidental `AttributeError` rather than the named-human validation error.

The one-way staged-state guard remained sound: a second release could not overwrite the first reviewer. HOLD lots still had no evidence pack, and no provider/customer/production send path exists in this synthetic/read-only shadow.

## Bounded repair

Current reviewed preimages before publication:
- source `a737c2e0f85c3a142d66b7691fad4ce5799b0ca4`
- test `f3c7557e34c8b6a4963060328bdde5c7f3985def`

Candidate blobs:
- source `e200a1f360a6f625dc114c12957bbebc0ec4c251`
- test `1cb641bbfe34776f7699fb37a27efc2898543d1a`

The repair normalizes reviewer whitespace, tokenizes across punctuation and numeric suffixes, rejects reserved automation/service tokens anywhere in the normalized label, requires at least two alphabetic name tokens, and fails closed for non-string reviewer values. The existing staged-state/single-transition release logic is unchanged.

The existing release regression now covers `System Reviewer`, `AI Reviewer`, `Bot Reviewer`, `service account`, `agent007 reviewer`, `pipeline/reviewer`, and non-string values; each denied attempt must leave the state digest unchanged. The valid `A. Reviewer` path and second-release denial remain covered.

## Executed acceptance

Using the connector-read current source/test plus the exact byte-preserving fixture and manifest content envelope, with only this bounded reviewer-gate change applied:
- focused unittest module: 9/9 PASS
- `py_compile` for source + test: PASS
- CLI acceptance: PASS
- 100 synthetic lots = 75 READY / 25 HOLD
- exact HOLD classes unchanged: 8 missing PO/quote, 5 duplicate container, 4 method out-of-scope, 4 chemistry/material mismatch, 4 QC fail
- 75 worksheets and 75 staged evidence packs
- full replay: 100 replayed, zero lots/jobs/worksheets/packs/holds/events added, state unchanged
- production writes: 0
- controlled payloads: 0

The first local reconstruction normalized the fixture JSON and correctly tripped its dataset SHA gate; the passing run above used the exact connector-read fixture bytes whose SHA256 is `4505796fb73e09c61a08203cd49ed7242c9eb08beb9b34ae44a7834a7b0f08e4`.

No live LIMS/QMS, controlled drawing, weapon, vehicle, propulsion, mission, provider/customer, compliance, outreach, spend, owner-PC, or force-push action is part of this repair.
