# Connector-native outbound seam lease

This package solves one narrow fleet problem: two connector workers can both read
"not sent" and cross an external provider boundary before either send is visible
to the other. The mutex must therefore be an atomic mutation that workers can
actually execute **before** Gmail/Slack/provider send.

There are two deterministic GitHub branch namespaces in
`woahwhattheheck/commons`:

```text
outbound-connector-lease/v1/<sha256(canonical cold/external seam JSON)>
outbound-connector-reply-lease/v2/<sha256(canonical provider-event JSON)>
```

`key.py` only compiles branch names. It never authorizes a send and performs no
network call. The decisive mutex event is the GitHub **create branch** result:

- exact create success: this worker acquired the seam prerequisite;
- `422 Reference already exists`: another worker/history owns it -> HOLD;
- timeout, permission error, transport error, or any indeterminate result -> HOLD.

Do not convert an ambiguous create into success by reading the branch afterward:
another worker may have created the same branch during the ambiguity window.

## Canonical seams

Callers do not supply a free-form composite opportunity string, so
price/contact/route fields cannot be smuggled into the hash schema.

### External opportunity — v1

Use when an authoritative issuer/source has a durable procurement, project, or
issue ID:

```json
{
  "kind": "external",
  "authority": "issuer.example",
  "id": "rfp-04254"
}
```

`buyer_scope` is the buyer organization's primary domain. `authority` is the
source/issuer domain, not the contacted person's mailbox. `id` is the stable
external identifier. A changed recipient, prime contact, quoted price, draft, or
route keeps the same buyer + source authority + source ID seam.

### Cold outreach — v1

Use `buyer_scope` plus exactly:

```json
{"kind":"cold"}
```

for unsolicited organization-level outreach with no durable external
opportunity. This intentionally permits only one cold seam per organization
until a real human/provider event creates a new state.

### Human reply event — v2

A human reply is already uniquely named by its provider plus durable inbound
event ID. The v2 seam therefore deliberately excludes buyer/contact/domain
classification:

```json
{
  "schema": "outbound-connector-reply-lease/v2",
  "provider": "gmail",
  "event_id": "<provider-message-id>"
}
```

This matters in a parallel swarm: two workers may classify the same person or
institution under different organization domains. If buyer scope participated in
the reply hash, they could acquire different locks and both answer the same human
message. Reply-v2 makes that impossible when workers use the canonical helper:
the same provider event always compiles to the same branch.

A legacy v1 reply document is deterministically migrated by `compile_document()`
to the provider-event-only v2 branch. New CLI calls must not supply
`--buyer-scope` for reply mode.

Automatic OOO/redirect messages do **not** become a new reply opportunity; stay
on the original external/cold seam. A genuinely new human inbound message has a
new durable provider event ID and can create one new reply-v2 seam.

## Required send sequence

This sequence is also a standing fleet invariant in `ground/SWARM_ORDER.md`.

1. Re-read provider truth and current coordination state.
2. Compile the canonical seam with `key.py`.
3. Atomically create that exact branch from current `main` through the connected
   GitHub provider **before any external provider mutation**.
4. If and only if the create itself succeeds, post the lease receipt/TAKE.
5. Re-read provider truth immediately before send. A historical/legacy send may
   predate the lease or v2 migration; if so, HOLD despite owning the branch.
6. Apply all normal owner/content/legal/payment/cooldown gates. The branch is
   mutual exclusion only.
7. Perform exactly one provider mutation.
8. Record the provider's canonical SENT/message receipt immediately and mark the
   seam DNR until a new human/provider event.
9. If the provider result is ambiguous, do not retry. Reconcile outcome only.

Branches are permanent one-touch state. Recovery from an abandoned lease
requires an explicit owner/fleet override tied to the original semantic seam;
workers must not mint a spelling/version/contact variant to evade it.

## CLI

External opportunity:

```bash
python -m revenue.outbound_connector_lease.key \
  --buyer-scope prime.example \
  --external-authority issuer.example \
  --external-id rfp-04254
```

Cold outreach:

```bash
python -m revenue.outbound_connector_lease.key \
  --buyer-scope example.com --cold
```

One human reply event — deliberately no buyer scope:

```bash
python -m revenue.outbound_connector_lease.key \
  --reply-provider gmail \
  --reply-event-id 1abc234
```

Reply-v2 strict JSON:

```json
{"schema":"outbound-connector-reply-lease/v2","provider":"gmail","event_id":"1abc234"}
```

## Validation

```bash
python -m py_compile revenue/outbound_connector_lease/key.py
python -m unittest -v revenue.outbound_connector_lease.test_key
python -O -m unittest -v revenue.outbound_connector_lease.test_key
```

The helper rejects URLs/emails as organization/source domains, normalizes domain
case/trailing dot/IDNA for cold/external seams, rejects duplicate/non-finite
JSON, uses exact field sets, and rejects price/contact/route/draft/subject fields
inside opportunity schemas. Reply-v2 accepts only provider + durable event ID and
therefore cannot be split by buyer-domain aliases. Determining actual buyer/source
authority is still a workflow evidence task for cold/external sends; reply event
identity comes from the provider itself.