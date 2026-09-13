---
name: outbound-send
description: >
  Safely perform external outreach or provider replies from a parallel swarm.
  Use before Gmail send, external Slack/DM, sponsor fallback, sales outreach,
  maintainer email, or any other externally visible message that another worker
  could duplicate.
license: Apache-2.0
metadata:
  author: commons
  version: "1"
  token: ""
---

# Outbound send — claim the seam before the provider

Parallel evidence preflights are not a mutex. Two workers can both observe no
prior send and both cross Gmail/provider before either receipt is visible. For
external mutations, acquire one deterministic GitHub branch seam first.

The branch is **mutual exclusion only**. It is never proof of owner approval,
content correctness, buyer acceptance, payment, or a successful provider send.
Never describe it as `external_send_authorized`.

## 1. Build one canonical seam

Use the closed schema in
[`revenue/outbound_connector_lease/README.md`](../../../revenue/outbound_connector_lease/README.md).

`buyer_scope` is the organization's primary domain, not a person's email or an
alternate subdomain chosen for convenience.

Choose exactly one opportunity mode:

1. **External opportunity:** source/issuer domain + stable authoritative ID.
   Procurement `04254` stays that same source ID whether the buyer contact,
   quoted price, route, draft, or subject changes.
2. **Cold:** exactly `{"kind":"cold"}` for unsolicited organization-level
   outreach with no external opportunity. Do not create product-specific cold
   aliases.
3. **Reply:** canonical provider + exact durable inbound message/event ID for one
   human reply that should be answered once. The v1 provider ID must be exactly
   one of `devpost`, `gmail`, `github`, `slack`, or `web-form`. Do not substitute
   aliases such as `email`, `googlemail`, `gmail-api`, `github-api`, `slack-api`,
   or `webform`; an unregistered provider spelling is HOLD until reviewed into
   the source registry.

The helper's exact-field schemas deliberately have no price, recipient, route,
subject, or draft fields. Do not encode those facts into the source ID.

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

# one human inbound event
python -m revenue.outbound_connector_lease.key \
  --buyer-scope example.com \
  --reply-provider gmail \
  --reply-event-id 1abc234
```

If this harness cannot run shell Python, reproduce the exact canonical JSON
schema and SHA-256. Do not invent a different encoding, provider alias, or a
free-form seam key.

## 2. Acquire through the connected GitHub provider

Target repository: `woahwhattheheck/commons`.

Create the exact branch returned by the helper from current `main` using the
connected GitHub **create branch** action.

Interpret the create result strictly:

- **create success** -> `SEAM_ACQUIRED`; continue.
- **422 / Reference already exists** -> `HOLD`; another worker/history owns it.
- **any other error, timeout, missing permission, or ambiguity** -> `HOLD`.

Do not retry under a new spelling, source authority, source ID, contact, price,
or provider alias. Do not read an existing branch and decide it must be yours
after an ambiguous create.

Post the acquired branch hash and semantic source identity to the relevant Slack
work thread as a TAKE. Slack visibility is not the atomic claim; GitHub create is.

## 3. Re-read provider truth, then send once

After lease success and immediately before mutation:

1. Search/read the authoritative provider for prior same-opportunity outbound and
   current inbound. Slack search miss alone is never clearance.
2. If an older same-seam send exists, **HOLD even though the branch is yours**;
   the message may predate this lease system.
3. Respect every separate owner/content/legal/cooldown/payment rule.
4. Send exactly once.
5. Immediately persist the provider SENT/message/thread ID and post a HARD DNR
   receipt for that seam until a new human/provider event.

If provider send returns an ambiguous error/timeout, do **not** retry. Switch to
outcome reconciliation: search provider SENT/thread state until success vs
failure is authoritative.

## 4. Replies and redirects

A real human inbound message can create one `reply` event seam using its exact
provider message/event ID and canonical provider ID. Reply in the existing
provider thread.

An automatic OOO, bounce redirect, or alternate-contact suggestion does **not**
mint a new opportunity. Stay on the original external/cold seam. This prevents
two workers from both following the same redirect before seeing each other's
provider send.

## 5. Never claim what the provider did not prove

- Branch created != email sent.
- SENT != human acceptance.
- Human interest != signed scope.
- Merge != bounty awarded.
- Award != payment settled.

Use canonical provider receipts for each state transition.

## Hostile checklist

Before any external send, make these questions boringly answerable:

- Would another contact at the same organization derive the same buyer scope?
- Is the opportunity sourced from the same issuer domain + exact authoritative ID?
- Can a different price/route/draft alter any lease field? (It must not.)
- Is the reply provider one exact reviewed canonical ID rather than an alias?
- Would an automatic redirect stay on the original opportunity seam?
- If two workers call create simultaneously, can only one observe exact success?
- If branch create is ambiguous, do we HOLD rather than mint a variant?
- If Gmail/provider result is ambiguous, do we reconcile rather than retry?

If any answer is no, HOLD and repair the seam before external mutation.
