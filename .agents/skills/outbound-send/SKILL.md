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
net-new external mutations, acquire one deterministic GitHub branch seam first.

The branch is **mutual exclusion only**. It is never proof of owner approval,
content correctness, buyer acceptance, payment, or a successful provider send.
Never describe it as `external_send_authorized`.

## 1. Name one canonical seam

Use the helper contract in
[`revenue/outbound_connector_lease/README.md`](../../../revenue/outbound_connector_lease/README.md).

- `buyer_scope` = organization primary domain, not a person's email.
- `opportunity_scope` = stable external opportunity/project/issue ID when one
  exists; otherwise exactly `cold` for unsolicited org-level outreach.
- One human inbound event that needs one reply may use
  `reply:<provider-message-id>`.
- Reuse an already-established opportunity key exactly.

Never create a new seam from recipient, contact, route, price, offer amount,
subject, version, revised draft, or alternate mailbox. Different `$5k`/`$7.5k`
proposals to the same procurement opportunity are the **same seam** unless the
owner explicitly creates a durable supersession outside this skill.

Compile the branch:

```bash
python -m revenue.outbound_connector_lease.key \
  --buyer-scope example.com \
  --opportunity-scope rfp-12345
```

If this harness cannot run shell Python, compute the same canonical JSON SHA-256
with any trustworthy local utility. Do not invent a different encoding.

## 2. Acquire through the connected GitHub provider

Target repository: `woahwhattheheck/commons`.

Create the exact branch returned by the helper from current `main` using the
connected GitHub **create branch** action.

Interpret the create result strictly:

- **create success** -> `SEAM_ACQUIRED`; continue.
- **422 / Reference already exists** -> `HOLD`; another worker/history owns it.
- **any other error, timeout, missing permission, or ambiguity** -> `HOLD`.

Do not retry under a new spelling. Do not read an existing branch and decide it
must be yours after an ambiguous create. Do not use another contact or another
price to bypass the branch.

Post the acquired branch hash/seam receipt to the relevant Slack work thread as a
TAKE so humans can route the work. Slack visibility is not the atomic claim; the
GitHub create result is.

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

A real human inbound reply can create a new one-reply event seam using the exact
provider message ID. Reply in the existing provider thread and bind one worker to
that event.

An auto-reply/OOO redirect to another contact does **not** mint a new opportunity.
Stay on the original org+opportunity seam. This prevents two workers from both
following the same redirect before seeing each other's provider send.

## 5. Never claim what the provider did not prove

- Branch created != email sent.
- SENT != human acceptance.
- Human interest != signed scope.
- Merge != bounty awarded.
- Award != payment settled.

Use canonical provider receipts for each state transition.

## Hostile checklist

Before any net-new send, make these questions boringly answerable:

- Would another contact at the same organization derive the same buyer scope?
- Would a different quoted price derive the same opportunity scope?
- Would a redirect derive the same original opportunity scope?
- If two workers call create simultaneously, can only one observe exact success?
- If the create response is ambiguous, do we HOLD rather than mint a variant?
- If Gmail/provider response is ambiguous, do we reconcile rather than retry?

If any answer is no, HOLD and repair the seam before external mutation.
