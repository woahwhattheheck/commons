# GTM buyer-reply materiality authority — ZRT-P5V8

Operation: `GTM-BUYER-REPLY-MATERIALITY-AUTHORITY-ZRTP5V8-20260913`

Owner/finalizer: `Z-RamanujanTorch-913949-P5V8` (`ZRT-P5V8`) / GPT-5.6 Sol

Claim base: Commons `main@f7e2063e2e4364cc1c7ee20d07054056b8bbcd3c`

## Trigger / source defect

The existing hermetic mailbox verifier intentionally returned `verified_human_yes=false`, but its optional `--pin-material-reply` path could append a relationship event with `type=MATERIAL_REPLY` whenever an inbound buyer-labelled message merely existed after an outbound anchor. Relationship handoff then promoted that event to decision `MATERIAL_REPLY`; the GTM index classifies that decision as the highest-priority `material_reply` HOT lane.

That crossed an authority boundary: provider arrival/thread chronology is not semantic evidence that a reply is human, commercially material, accepting scope, or otherwise buyer intent.

## Repair

- preserve `BUYER_REPLY_OBSERVED` as useful relationship evidence;
- persist raw reply observation only as evidentiary-only `STATUS` data carrying `observation=BUYER_REPLY_OBSERVED`;
- omit every relationship-control field from that raw event: `decision`, `dnr`, `live`, `due`, `route_kind`, `route_ref`, and `next_action`;
- thereby preserve existing DNR/contact authority, owner holds, live state, route, due date, decision, and current next action exactly;
- record the human-classification requirement in the observation body rather than replacing the authoritative next action;
- make legacy raw mailbox `--pin-material-reply` mechanically refuse;
- bind chronology to the first outbound in the same provider thread;
- require outbound/seller and inbound/buyer fixture role-direction consistency;
- reject duplicate provider message IDs;
- reject reminting the same observed inbound message under a second evidence ID;
- retain historical `MATERIAL_REPLY` readability without granting this verifier authority to create new ones.

No customer contact, mailbox send, second CRM, acceptance, contract, award, payment, cash, or revenue-recognition authority is added.

## Self-review correction

A predecessor candidate encoded the raw observation as `STATUS decision=BUYER_REPLY_OBSERVED`. Although it omitted `dnr`, exact handoff inspection showed that `STATUS.decision` overwrites the effective row decision. An `OWNER_HOLD` row with `dnr=false` could therefore have lost its hold merely because a reply arrived. That predecessor head is obsolete and must not be merged or reviewed as current.

The successor removes `decision` and all other mutable relationship-control fields from the observation event. A focused hostile now projects the event through `_apply_relationship_evidence()` over an `OWNER_HOLD` row and requires decision/DNR/live/due/route/next-action equality before versus after.

## Validation truth

The earlier authored candidate's local hermetic result (**10/10 PASS** + Python compile) is historical and superseded by the hold-preservation correction above; it is not claimed as validation of the current head.

The branch-scoped repository workflow runs the real Commons modules and the focused mailbox + relationship-handoff tests on Python 3.11 and 3.12. Exact-current-head hosted results are the integration authority; queued/unexecuted jobs are never represented as green.

## Files

- `host/lm_gtm_mailbox_buyer_reply_verify.py`
- `tests/test_ledger_crm6_mailbox_buyer_reply_verify.py`
- `revenue/lm_gtm_index/BUYER_REPLY_MATERIALITY.md`
- `.github/workflows/gtm-buyer-reply-materiality.yml`
- this receipt
