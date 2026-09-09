# SOL-REVIEW-TPOLAR — named-human reviewer guard repair

Demand: `trace-polar-as9100-lims-01`
Source PR reviewed: #11191 (merge `5c08d2c298813ddc8d228cf6c283ba2fa86073bb`)
Repair date: 2026-09-09

## Reproduced defect

Merged `_named_human()` intended to reject automation/service identities, but it only checked the complete label and hyphen-delimited pieces. The exact merged logic accepted obvious two-token automation labels including `System Operator`, `AI Reviewer`, `bot user`, `service account`, and `Agent Reviewer`. A `REVIEW_READY` W1 evidence pack could therefore receive an `APPROVED_FOR_HUMAN_DISPOSITION` copy under one of those labels. W2/W3 held-pack gates remained intact, the disposition remained copy-only, and `sent` remained false.

Baseline exact-function reproducer: all five labels above were accepted.

## Repair

Current-main preimage for `trace_polar_as9100.py`: blob `028b4fc1df1c0078623f03be65a87ae85631bf9d`.

The repair tokenizes normalized reviewer labels across Unicode punctuation/whitespace and rejects any token present in the existing reserved automation vocabulary. It preserves the existing minimum-two-token rule and does not alter replay, fixture, hold, evidence, or send behavior.

Created repair blob: `423d5fc1ca02f7c9b85262b7ce62c87d11a17cb6`.
Focused regression blob: `b7a65390bec178dace7762cbb3d72865fec9deff` (`test_reviewer_identity_guard.py`).

## Verification performed before publication

- Baseline exact-function reproducer: `System Operator`, `AI Reviewer`, `bot user`, `service account`, and `Agent Reviewer` all reproduced as accepted.
- Patched exact-function assertions: 11/11 PASS — nine reserved automation labels across space, slash, dot, colon, and underscore delimiters reject; `Jordan Reviewer` and `Ana María` accept.
- PR repair diff must remain limited to the existing source plus the focused regression and this receipt; no fixture/manifest/README/product-state edits are permitted.
- Existing PR #11191 acceptance remains the source baseline: 3 wafers / 36 steps, W1 REVIEW_READY, W2 HOLD_REVISION, W3 HOLD_CAL_AND_SIGNATURE, three exception rows, three packs, zero-add replay, held-pack approval blocked, automatic disposition disabled.

The local shell could not resolve `raw.githubusercontent.com`, so this receipt does not claim a fresh execution of the full 10-test module from downloaded repository bytes. Publication verification therefore relies on connector-read preimages, exact Git diff/readback, the isolated exact-function reproducer above, and the new focused regression source. No shell/network failure is treated as a GitHub connector failure.

No live QMS, traveler, recipe, NCR, instrument, material, production, disposition, certification, customer/provider, external-send, spend, or force-push action is part of this repair.
