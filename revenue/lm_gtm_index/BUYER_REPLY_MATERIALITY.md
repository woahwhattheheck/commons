# Buyer reply materiality authority

Operation: `GTM-BUYER-REPLY-MATERIALITY-AUTHORITY-ZRTP5V8-20260913`

Provenance fix-forward: `GTM-BUYER-REPLY-OBSERVATION-PROVENANCE-ZRTP5V8-20260913`

Mailbox transport evidence and commercial semantics are separate trust layers.

## Evidence levels

### `BUYER_REPLY_OBSERVED`

This means only that the mailbox verifier observed an inbound message labelled as a buyer message after an outbound SENT anchor in the **same provider thread**. It is provider/thread/chronology evidence.

It does **not** establish that the sender is a verified human decision-maker, that the message is commercially material, that the buyer wants to proceed, that scope or terms are accepted, that an award exists, or that payment occurred. It is deliberately not a HOT GTM lane.

The hermetic verifier may persist this only as evidentiary-only relationship `STATUS` data with `observation=BUYER_REPLY_OBSERVED`. That record intentionally omits every handoff control field: `decision`, `dnr`, `live`, `due`, `route_kind`, `route_ref`, and `next_action`. The handoff can therefore learn that a reply arrived without dissolving an existing owner hold, weakening a DNR, changing a route/due date, or replacing the current next action.

Pinning also reacquires the observation from the repository's canonical current hermetic fixture. A caller-supplied verifier result is compatibility input only: it must canonically equal the reacquired result, and the persisted source message IDs come from the reacquired result. The evidence-output `paths` argument cannot select a different mailbox verification root. This prevents a forged `BUYER_REPLY_OBSERVED` object from asserting reply provenance for a `NO_BUYER_REPLY` target or inventing arbitrary Gmail source IDs.

Human classification is required before any material-reply or commercial-state claim, but the raw observation itself does not overwrite the relationship's authoritative next action.

### `MATERIAL_REPLY`

`MATERIAL_REPLY` is a semantic commercial classification. It may become the highest-priority GTM lane, so it requires separate evidence for the message's meaning and authority. Raw mailbox arrival/thread chronology is insufficient and the mailbox verifier is mechanically forbidden from minting it.

Historical `MATERIAL_REPLY` evidence remains readable for compatibility. Consumers should inspect its provenance before treating it as current commercial authority.

## Fail-closed rules

- Duplicate provider message IDs in one fixture are rejected.
- Fixture direction/role is coherent: outbound messages are seller-role anchors and inbound messages are buyer-role observations.
- Inbound chronology is bound to the first outbound anchor in the same thread, not to an unrelated older outbound in another thread.
- The same inbound provider message cannot be reminted under multiple `BUYER_REPLY_OBSERVED` evidence IDs.
- A pin operation recomputes the canonical current verification for its target subject; caller-supplied verification data must match exactly.
- Evidence-destination path overrides do not override the canonical verification root.
- Legacy `--pin-material-reply` remains as a compatibility surface but always refuses.
- Auto-acks, support tickets, out-of-office replies, routing mail, unknown replies, and other inbound existence evidence cannot become material buyer interest merely because a message arrived.
- Raw arrival cannot alter decision, DNR/contact authority, owner-hold authority, live state, route, due date, or next action.
- No mailbox send, CRM remint, acceptance, contract, payment, award, or revenue-recognition authority is added by this repair.

## CLI

Observe and optionally persist evidentiary-only relationship data:

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
