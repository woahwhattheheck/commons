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

A branch create is also not a durable one-touch witness when the ref can later be
deleted or updated. Until current host rules for the exact ref are independently
verified, the machine ceiling is:

```text
state=HOLD_REF_ROLLBACK_PROTECTION_UNVERIFIED
ref_rollback_protection_required=true
ref_rollback_protection_verified=false
branch_create_authority=false
production_mutex_complete=false
external_send_authorized=false
```

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
3. **Host ref rollback protection.** Read the rules currently applicable to the
   exact connector branch. Require active deletion and update/non-fast-forward
   protection with no fleet worker or GitHub App bypass. Retain the provider rule
   generation. Missing, disabled, evaluate-only, ambiguous, or bypassable rules
   mean `HOLD_REF_ROLLBACK_PROTECTION_UNVERIFIED`.
4. **Canonical opportunity/reply seam.** Build the exact connector identity and,
   only after step 3 is proven, atomically acquire the exact protected branch.
5. **Provider readback and all independent gates.** Re-read provider truth, then
   apply owner/content/legal/route/cooldown/payment rules before at most one
   provider mutation.

If a later prerequisite fails after an organization-wide lease was acquired,
follow that authority's own release/expiry contract. Do not improvise an unlock,
mint a new organization spelling, or reverse lock order.

## 1. Build one canonical opportunity/reply seam

Use the closed schema in
[`revenue/outbound_connector_lease/README.md`](../../../revenue/outbound_connector_lease/README.md).
The scoped authority ceiling and migration rule are in
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
python -m revenue.outbound_connector_lease.key \
  --buyer-scope prime.example \
  --external-authority issuer.example \
  --external-id rfp-04254

python -m revenue.outbound_connector_lease.key \
  --buyer-scope example.com --cold

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

## 2. Prove host ref rollback protection

Target repository: `woahwhattheheck/commons`.

Before any create attempt, use the connected GitHub provider to read the rules
applicable to the exact candidate branch. The retained response must show an
active rule generation that blocks deletion, update, and non-fast-forward
mutation for the branch family and gives no fleet worker/GitHub App a bypass.
Repository source files, a ruleset-candidate JSON file, a branch protection README,
or a worker assertion are not host authority.

Treat every one of these as HOLD:

- no applicable host rules;
- evaluate-only or disabled enforcement;
- deletion allowed;
- update/non-fast-forward allowed;
- a bypass available to the same worker/App that performs coordination writes;
- timeout, permission error, stale snapshot, or any ambiguous rules readback.

The current v1 history predates independently proven protection. An absent v1 ref
is not proof that it was never created and deleted. Use only a reviewed protected
cutover generation or an independently monotonic witness. Never mint v2 merely
to evade an existing v1 seam.

## 3. Acquire the opportunity/reply seam through the connected GitHub provider

Only after step 2 is authoritative, create the exact branch returned by the
helper from current `main` using the connected GitHub **create branch** action.

Interpret the result strictly:

- **create success + independently verified protection** ->
  `OPPORTUNITY_SEAM_ACQUIRED`; continue to remaining gates.
- **create success while protection is unverified** ->
  `HOLD_REF_ROLLBACK_PROTECTION_UNVERIFIED`.
- **422 / Reference already exists** -> `HOLD`; another worker/history owns it.
- **any other error, timeout, missing permission, or ambiguity** -> `HOLD`.

Do not retry under a new spelling, source authority, source ID, contact, price,
provider alias, buyer domain, or subdomain. Do not read an existing branch and
decide it must be yours after an ambiguous create.

Post the acquired branch hash, retained host-rule generation, and semantic source
identity to the relevant Slack work thread as a TAKE. Slack visibility is not the
atomic claim; the protected GitHub create is. Exact connector-branch success still
does **not** establish organization-wide exclusivity or production readiness.

## 4. Re-read provider truth, then send once

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
outcome reconciliation: search provider SENT/thread state until success versus
failure is authoritative.

## 5. Replies and redirects

A real human inbound message can create one `reply` event seam using its exact
provider message/event ID and canonical provider ID. Reply in the existing
provider thread.

An automatic OOO, bounce redirect, or alternate-contact suggestion does **not**
mint a new opportunity. Stay on the original external/cold seam. This prevents
two workers from both following the same redirect before seeing each other's
provider send.

## 6. Never claim what the provider did not prove

- Organization lease created != opportunity seam acquired.
- Identity validated != ref rollback protection verified.
- Branch created != durable protected branch authority.
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
- Can the exact connector ref be deleted or updated after create? If yes, HOLD.
- Does current host readback prove active deletion and update protection with no
  worker/App bypass for the exact ref? If not, HOLD.
- Could pre-protection v1 absence mean “created then deleted”? If yes, HOLD or use
  the reviewed protected cutover generation.
- If two workers call create for the same protected seam simultaneously, can only
  one observe exact success?
- If any rules or branch create is ambiguous, do we HOLD rather than mint a
  variant?
- If Gmail/provider result is ambiguous, do we reconcile rather than retry?

If any answer is no, HOLD and repair the applicable scope/seam before external
mutation.
