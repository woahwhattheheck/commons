---
name: outbound-send
description: >
  Safely perform external outreach or provider replies from a parallel swarm.
  Use before Gmail send, external Slack/DM, sponsor fallback, sales outreach,
  maintainer email, form submission, or any other externally visible message
  that another worker could duplicate.
license: Apache-2.0
metadata:
  author: commons
  version: "2"
  token: ""
---

# Outbound send — claim the seam before the provider

Parallel evidence preflights are not a mutex. Two workers can both observe no
prior send and both cross Gmail/provider before either receipt is visible. For
external mutations, acquire one deterministic GitHub branch seam first.

This is a standing fleet precondition, not an optional optimization. The branch
is **mutual exclusion only**. It is never proof of owner approval, content
correctness, buyer acceptance, payment, or a successful provider send. Never
describe it as `external_send_authorized`.

## 1. Build one canonical seam

Use the closed schemas in
[`revenue/outbound_connector_lease/README.md`](../../../revenue/outbound_connector_lease/README.md).

Choose exactly one opportunity mode:

1. **External opportunity:** buyer primary domain + source/issuer domain + stable
   authoritative ID. Procurement `04254` stays that same source ID whether the
   buyer contact, quoted price, route, draft, or subject changes.
2. **Cold:** buyer primary domain + exactly `{"kind":"cold"}` for unsolicited
   organization-level outreach with no external opportunity. Do not create
   product-specific cold aliases.
3. **Reply v2:** provider + exact durable inbound message/event ID. **Buyer,
   contact, route, thread label, recipient domain, and organization
   classification are not reply-seam inputs.** One provider event gets one
   global reply mutex even when workers disagree about the organization.

The helper's exact-field schemas deliberately have no price, recipient, route,
subject, or draft fields. Do not encode those facts into an ID.

Examples:

```bash
# externally identified opportunity
python -m revenue.outbound_connector_lease.key \
  --buyer-scope prime.example \
  --external-authority issuer.example \
  --external-id rfp-04254

# generic cold outreach
python -m revenue.outbound_connector_lease.key \
  --buyer-scope example.com --cold

# one human inbound event — deliberately NO buyer scope
python -m revenue.outbound_connector_lease.key \
  --reply-provider gmail \
  --reply-event-id 1abc234
```

If this harness cannot run shell Python, reproduce the exact canonical JSON
schema and SHA-256. Do not invent a different encoding or a free-form seam key.

## 2. Acquire through the connected GitHub provider

Target repository: `woahwhattheheck/commons`.

Create the exact branch returned by the helper from current `main` using the
connected GitHub **create branch** action **before any external provider
mutation**.

Interpret the create result strictly:

- **create success** -> `SEAM_ACQUIRED`; continue.
- **422 / Reference already exists** -> `HOLD`; another worker/history owns it.
- **any other error, timeout, missing permission, or ambiguity** -> `HOLD`.

Do not retry under a new spelling, source authority, source ID, buyer domain,
contact, price, or a downgraded legacy reply seam. Do not read an existing branch
and decide it must be yours after an ambiguous create.

Post the acquired branch hash and semantic source identity to the relevant Slack
work thread as a TAKE. Slack visibility is not the atomic claim; GitHub create is.

## 3. Re-read provider truth, then send once

After lease success and immediately before mutation:

1. Search/read the authoritative provider for prior same-opportunity outbound and
   current inbound. Slack search miss alone is never clearance.
2. If an older same-seam send exists, **HOLD even though the branch is yours**;
   the message may predate this lease system or a reply-v2 migration.
3. Respect every separate owner/content/legal/cooldown/payment rule.
4. Send exactly once.
5. Immediately persist the provider SENT/message/thread ID and post a HARD DNR
   receipt for that seam until a new human/provider event.

If provider send returns an ambiguous error/timeout, do **not** retry. Switch to
outcome reconciliation: search provider SENT/thread state until success vs
failure is authoritative.

## 4. Replies and redirects

A real human inbound message creates one reply-v2 event seam using only its exact
provider + durable provider message/event ID. Reply in the existing provider
thread. Different guesses about buyer domain, institution, contact, or route must
still derive the same reply branch.

A new human inbound message has a new provider event ID and can therefore create
one new reply seam. An automatic OOO, bounce redirect, or alternate-contact
suggestion does **not** mint a new opportunity. Stay on the original external/cold
seam. This prevents two workers from both following the same redirect before
seeing each other's provider send.

## 5. Never claim what the provider did not prove

- Branch created != email sent.
- SENT != human acceptance.
- Human interest != signed scope.
- Merge != bounty awarded.
- Award != payment settled.

Use canonical provider receipts for each state transition.

## Hostile checklist

Before any external send, make these questions boringly answerable:

- For cold/external: would another contact at the same organization derive the
  same buyer scope?
- For reply: would **any** worker with the same provider event ID derive the same
  branch even if they classify the buyer differently?
- Is the external opportunity sourced from the same issuer domain + exact
  authoritative ID?
- Can a different price/route/draft/contact alter any lease field? (It must not.)
- Would an automatic redirect stay on the original opportunity seam?
- If two workers call create simultaneously, can only one observe exact success?
- If branch create is ambiguous, do we HOLD rather than mint a variant?
- If Gmail/provider result is ambiguous, do we reconcile rather than retry?

If any answer is no, HOLD and repair the seam before external mutation.