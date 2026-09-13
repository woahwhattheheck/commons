# Buyer reply materiality authority

Operation: `GTM-BUYER-REPLY-MATERIALITY-AUTHORITY-ZRTP5V8-20260913`

Mailbox transport evidence and commercial semantics are separate trust layers.

## Evidence levels

### `BUYER_REPLY_OBSERVED`

This means only that the mailbox verifier observed an inbound message labelled as a buyer message after an outbound SENT anchor in the **same provider thread**. It is provider/thread/chronology evidence.

It does **not** establish that the sender is a verified human decision-maker, that the message is commercially material, that the buyer wants to proceed, that scope or terms are accepted, that an award exists, or that payment occurred. It is deliberately not a HOT GTM lane.

The hermetic verifier may persist this state only as relationship `STATUS` evidence with `decision=BUYER_REPLY_OBSERVED` and `HUMAN_CLASSIFICATION_REQUIRED` as the next action.

### `MATERIAL_REPLY`

`MATERIAL_REPLY` is a semantic commercial classification. It may become the highest-priority GTM lane, so it requires separate evidence for the message's meaning and authority. Raw mailbox arrival/thread chronology is insufficient and the mailbox verifier is mechanically forbidden from minting it.

Historical `MATERIAL_REPLY` evidence remains readable for compatibility. Consumers should inspect its provenance before treating it as current commercial authority.

## Fail-closed rules

- Duplicate provider message IDs in one fixture are rejected.
- Inbound chronology is bound to the first outbound anchor in the same thread, not to an unrelated older outbound in another thread.
- The same inbound provider message cannot be reminted under multiple `BUYER_REPLY_OBSERVED` evidence IDs.
- Legacy `--pin-material-reply` remains as a compatibility surface but always refuses.
- Auto-acks, support tickets, out-of-office replies, routing mail, unknown replies, and other inbound existence evidence cannot become material buyer interest merely because a message arrived.
- No mailbox send, CRM remint, acceptance, contract, payment, award, or revenue-recognition authority is added by this repair.

## CLI

Observe and optionally persist neutral relationship evidence:

```sh
python3 host/lm_gtm_mailbox_buyer_reply_verify.py SUBJECT
python3 host/lm_gtm_mailbox_buyer_reply_verify.py SUBJECT \
  --pin-buyer-reply-observed \
  --organization "Organization"
```

The old promotion route now fails closed:

```sh
python3 host/lm_gtm_mailbox_buyer_reply_verify.py SUBJECT \
  --pin-material-reply \
  --organization "Organization"
```

A later semantic reviewer may establish a genuinely material reply using separately sourced evidence and the appropriate relationship/CRM authority path. That decision is intentionally outside the mailbox-existence verifier.
