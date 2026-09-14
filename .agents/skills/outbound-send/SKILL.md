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

# Outbound send — claim scoped seams before the provider

Parallel evidence preflights are not a mutex. Two workers can both observe no
prior send and both cross Gmail/provider before either receipt is visible.
External mutations therefore require atomic coordination before the provider.

The connector branch in this skill is **one opportunity/reply mutex only**. It is
never proof of owner approval, organization-wide exclusivity, content
correctness, buyer acceptance, payment, or a successful provider send. Never
describe it as `external_send_authorized` or as the sole production mutex.

`key.py` normalizes domain syntax but does not prove that a caller supplied the
one authoritative organization identity. Distinct opportunities at one buyer and
buyer-domain aliases can intentionally produce distinct connector branches.

## 0. Fixed coordination order

Before an external mutation, use this order and never reverse it to race a peer:

1. **Authoritative organization scope.** Resolve the buyer from current retained
   organization identity evidence. A convenient subdomain, alternate brand
   domain, guessed alias, or stale mapping is not authority. If canonical scope
   is unresolved, `HOLD`.
2. **Organization-wide atomic pressure/mutex when required by the send path.**
   Net-new prospecting and other paths exposed to cross-opportunity pile-on must
   satisfy the current landed, independently validated organization-wide control
   before the opportunity seam. An unmerged/SOURCE-RED carrier is not authority;
   if the required landed control is unavailable or ambiguous, `HOLD`.
3. **Canonical opportunity/reply seam.** Build and atomically acquire the exact
   connector branch below.
4. **Provider readback and all independent gates.** Re-read provider truth, then
   apply owner/content/legal/route/cooldown/payment rules before at most one
   provider mutation.

If a later prerequisite fails after an organization-wide lease was acquired,
follow that authority's own release/expiry contract. Do not improvise an unlock,
mint a new organization spelling, or reverse lock order.

## 1. Build one canonical opportunity/reply seam

Use the closed schema in
[`revenue/outbound_connector_lease/README.md`](../../../revenue/outbound_connector_lease/README.md).
The scoped authority ceiling and legacy migration rule are in
[`revenue/outbound_connector_lease/AUTHORITY.md`](../../../revenue/outbound_connector_lease/AUTHORITY.md).

`buyer_scope` must come from authoritative organization-scope evidence and should
be the organization's primary domain, not a person's email or an alternate
subdomain chosen for convenience. The key compiler checks syntax; it does not
prove this semantic choice.

Choose exactly one opportunity mode:

1. **External opportunity:** source/issuer domain + stable authoritative ID.
   Procurement `04254` stays that same source ID whether the buyer contact,
   quoted price, route, draft, or subject changes. Source identity must itself be
   authoritative; an alternate portal/domain chosen by a worker is not a safe
   alias.
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

Do **not** use `revenue/outbound_mutex` as a replacement seam. Its free-form
opportunity key is legacy/reference CAS and is non-authoritative for this layer.

## 2. Acquire the opportunity/reply seam through the connected GitHub provider

Target repository: `woahwhattheheck/commons`.

Create the exact branch returned by the helper from current `main` using the
connected GitHub **create branch** action.

Interpret the create result strictly:

- **create success** -> `OPPORTUNITY_SEAM_ACQUIRED`; continue to remaining gates.
- **422 / Reference already exists** -> `HOLD`; another worker/history owns it.
- **any other error, timeout, missing permission, or ambiguity** -> `HOLD`.

Do not retry under a new spelling, source authority, source ID, contact, price,
provider alias, buyer domain, or subdomain. Do not read an existing branch and
decide it must be yours after an ambiguous create.

Post the acquired branch hash and semantic source identity to the relevant Slack
work thread as a TAKE. Slack visibility is not the atomic claim; GitHub create is.
Exact connector-branch success still does **not** establish organization-wide
exclusivity or production readiness.

## 3. Re-read provider truth, then send once

After every required coordination layer succeeds and immediately before mutation:

1. Search/read the authoritative provider for prior same-opportunity outbound and
   current inbound. Slack search miss alone is never clearance.
2. If an older same-seam send exists, **HOLD even though the branch is yours**;
   the message may predate this lease system.
3. Respect every separate owner/content/legal/route/cooldown/payment rule.
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

- Organization lease created != opportunity seam acquired.
- Opportunity branch created != email sent.
- SENT != human acceptance.
- Human interest != signed scope.
- Merge != bounty awarded.
- Award != payment settled.

Use canonical provider receipts for each state transition.

## Hostile checklist

Before any external send, make these questions boringly answerable:

- Is `buyer_scope` backed by authoritative organization identity rather than a
  syntactically valid caller choice?
- Could an alternate domain/subdomain identify the same organization? If yes,
  where is the authoritative mapping/generation that collapses it?
- If cold and external work, or two distinct external opportunities, race at the
  same organization, which organization-wide atomic control prevents pile-on?
- Is the opportunity sourced from the same authoritative source identity + exact
  stable ID rather than an alternate portal/domain spelling?
- Can a different price/route/draft alter any connector seam field? (It must not.)
- Is the reply provider one exact reviewed canonical ID rather than an alias?
- Would an automatic redirect stay on the original opportunity seam?
- If two workers call create for the same connector seam simultaneously, can only
  one observe exact success?
- If any branch/lease create is ambiguous, do we HOLD rather than mint a variant?
- If Gmail/provider result is ambiguous, do we reconcile rather than retry?

If any answer is no, HOLD and repair the applicable scope/seam before external
mutation.
