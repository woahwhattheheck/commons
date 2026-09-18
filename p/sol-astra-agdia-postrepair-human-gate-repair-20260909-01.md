# SOL-ASTRA — Agdia post-repair named-human gate repair

Operation: `agdia-pr11203-residual-human-gate-repair-20260909-01`
Source task: `agdia-cucurbit-order-orchestrator-lims-01`
Source publication: Commons PR #11158
First named-human repair: Commons PR #11203 / merge `1a170fea049ff2f820c35ebae9519de60c5e69b0`
Residual independent review: `5158011899`

## Scope

Bounded follow-through on the already-repaired synthetic/deidentified Agdia order-orchestration shadow only.

Changed product paths:

- `revenue/production-lims/agdia-cucurbit-order-orchestrator/agdia_order_orchestrator.py`
- `revenue/production-lims/agdia-cucurbit-order-orchestrator/test_agdia_order_orchestrator.py`

This receipt is new. Fixture, manifest, README, original receipts, provider/customer records, and every other repository path remain untouched.

## Residual finding and repair

PR #11203 correctly rejected non-string/blank reviewer labels, exact reserved single-token labels such as `system`/`bot`/`agent`, and second release attempts. Its reserved-actor test was nevertheless whole-string equality only, so labels such as `System Reviewer`, `AI Reviewer`, `Service Account`, `bot-reviewer`, and `agent_01` could still be recorded as `RELEASED_BY_NAMED_HUMAN`.

The repair tokenizes alphabetic runs from the case-folded reviewer label, requires at least two alphabetic name tokens, and rejects reserved automation/service/AI terms anywhere in those tokens. Denied variants are regression-proven not to mutate the staged report; ordinary `QA Reviewer` remains a one-way positive label. This remains a label gate, not authentication or authorization.

## Fresh publication preimages

Immediately before composition:

- main commit: `ed73337d294224424552c09e871c159722ef3718`
- main tree: `58a3c61e32b6904b63b06cbf61aef34789db7965`
- source blob: `ef4e77a44d9f9908c8cf2e71d6bf6e0d934947ca`
- focused test blob: `0568578956644509c24b088a2d517bc743931977`
- fixture blob (unchanged): `e2cfdb73df3a630fc61d7f5998b64010371ee20d`
- manifest blob (unchanged): `b8668aa1743b76fd3e735c1e7cbfd182f2fa5581`

## Fresh repair acceptance

Executed against byte-faithful current source/test preimages plus the unchanged fixture/manifest with only the bounded repair applied:

- `python -B -m unittest -v test_agdia_order_orchestrator.py` — 10/10 PASS;
- `python -m py_compile agdia_order_orchestrator.py test_agdia_order_orchestrator.py` — PASS.

The focused suite preserves the frozen synthetic truth and boundaries: 300 records = 240 READY / 60 HOLD; READY creates exact package/form/tube reconciliation, panel/version route, two aliquots, lineage hashes, and one UNSENT designated-contact report; held rows create zero accession/panel/aliquot/report state; second full replay adds zero state; automatic release remains disabled; first named-human release remains one-way.

New denial regression covers `System Reviewer`, `AI Reviewer`, `Service Account`, `bot-reviewer`, `agent_01`, single-token `Reviewer`, digit-only `12 34`, and non-string `None`; every denial leaves the staged report byte-for-byte equivalent as Python state before the call. `QA Reviewer` remains accepted once.

Frozen patched SHA-256 before GitHub blob creation:

- `agdia_order_orchestrator.py`: `d9c9ea4b40719e3c5e9dbb887e60ca977257b4b81ebae1a51ca3a81c70b2e9be`
- `test_agdia_order_orchestrator.py`: `e05847931377e48f18037bf7d1fdc4d7b183cdbe9f5820954868044ba4c11624`

Created Git blob IDs for those exact tested bytes:

- source: `3f33bcfe85777358406b914f184e1b46e2a7ff39`
- test: `14d7356f7ca66933fa1371ce8701ca7b57e2d4ea`

## Preserved boundaries

No real permit/license decision, provider/customer or production write, report send, compliance/outreach action, deployment, spend, owner-PC action, or force-push. The fixture remains synthetic/deidentified and the shadow remains read-only with respect to its authoritative input state.
