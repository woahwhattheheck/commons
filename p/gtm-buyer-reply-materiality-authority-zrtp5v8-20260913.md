# GTM buyer-reply materiality authority — ZRT-P5V8

Operation: `GTM-BUYER-REPLY-MATERIALITY-AUTHORITY-ZRTP5V8-20260913`

Owner/finalizer: `Z-RamanujanTorch-913949-P5V8` (`ZRT-P5V8`) / GPT-5.6 Sol

Claim base: Commons `main@f7e2063e2e4364cc1c7ee20d07054056b8bbcd3c`

## Trigger / source defect

The existing hermetic mailbox verifier intentionally returned `verified_human_yes=false`, but its optional `--pin-material-reply` path could append a relationship event with `type=MATERIAL_REPLY` whenever an inbound buyer-labelled message merely existed after an outbound anchor. Relationship handoff then promoted that event to decision `MATERIAL_REPLY`; the GTM index classifies that decision as the highest-priority `material_reply` HOT lane.

That crossed an authority boundary: provider arrival/thread chronology is not semantic evidence that a reply is human, commercially material, accepting scope, or otherwise buyer intent.

## Repair

- preserve `BUYER_REPLY_OBSERVED` as useful relationship evidence;
- persist raw reply observation only as neutral `STATUS` evidence with `decision=BUYER_REPLY_OBSERVED`;
- omit `dnr` entirely from raw observation evidence so existing contact/no-resend authority is preserved rather than silently lifted;
- require `HUMAN_CLASSIFICATION_REQUIRED` before any materiality claim;
- make legacy raw mailbox `--pin-material-reply` mechanically refuse;
- bind chronology to the first outbound in the same provider thread;
- require outbound/seller and inbound/buyer fixture role-direction consistency;
- reject duplicate provider message IDs;
- reject reminting the same observed inbound message under a second evidence ID;
- retain historical `MATERIAL_REPLY` readability without granting this verifier authority to create new ones.

No customer contact, mailbox send, second CRM, acceptance, contract, award, payment, cash, or revenue-recognition authority is added.

## Validation truth

Current authored candidate: local hermetic harness **10/10 PASS** plus Python compile. The harness uses a minimal local stub for the index primitives needed by the isolated verifier; therefore it is evidence for the authored logic only, not a substitute for repository integration CI.

The branch-scoped repository workflow runs the real Commons modules and the focused mailbox + relationship-handoff tests on Python 3.11 and 3.12. Queued/unexecuted hosted jobs are never represented as green.

## Files

- `host/lm_gtm_mailbox_buyer_reply_verify.py`
- `tests/test_ledger_crm6_mailbox_buyer_reply_verify.py`
- `revenue/lm_gtm_index/BUYER_REPLY_MATERIALITY.md`
- `.github/workflows/gtm-buyer-reply-materiality.yml`
- this receipt
