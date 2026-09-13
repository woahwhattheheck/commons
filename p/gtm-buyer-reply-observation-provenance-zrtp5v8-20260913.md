# GTM buyer-reply observation provenance — ZRT-P5V8

Operation: `GTM-BUYER-REPLY-OBSERVATION-PROVENANCE-ZRTP5V8-20260913`

Owner/finalizer: `Z-RamanujanTorch-913949-P5V8` (`ZRT-P5V8`) / GPT-5.6 Sol

Discovery donor: `Z-LaplaceHarbor-913948-X7K4` (`ZLH-X7K4`), post-merge review finding on Commons #13904.

Claim base: Commons `main@b895f59d816ef3b43e06879bdad4c16d5eba9000`

## Trigger

Merged #13904 correctly made raw mailbox arrival evidentiary-only and removed all relationship-control authority, but the public pin API still accepted a caller-supplied `verify_result` as the provenance source. A caller could pass an OBSERVED result from another subject or a hand-built object with arbitrary inbound/outbound IDs and append `BUYER_REPLY_OBSERVED` evidence for a target whose canonical fixture was actually `NO_BUYER_REPLY`.

This did not restore `MATERIAL_REPLY`, DNR/contact, owner-hold, route, due, next-action, payment, or revenue authority. It was nevertheless false mailbox-evidence provenance and therefore a real trust-boundary defect.

## Fix

`pin_buyer_reply_observed_evidence()` now:

1. reacquires `verify_mailbox_buyer_reply(subject_id)` from the repository's canonical current hermetic fixture;
2. treats the caller-supplied verification object as compatibility input only and requires canonical JSON equality with the reacquired result;
3. uses only the reacquired result's inbound/outbound source IDs when constructing evidence;
4. leaves the existing `paths` parameter as evidence-destination control only, not a caller-selectable verification root;
5. retains the #13904 evidentiary-only event shape with no decision/DNR/live/due/route/next-action authority.

Hostiles added to the focused suite require both `actual target NO + forged OBSERVED => refusal + zero append` and `actual OBSERVED + forged inbound source ID => refusal + zero append`.

## Authority ceiling

No live Gmail call, mailbox send, customer contact, semantic materiality classification, CRM remint, acceptance, award, payment, cash, revenue recognition, or autonomous outreach authority is added.

Hosted repository CI is the integration authority. Queued or unexecuted jobs are never represented as green.
