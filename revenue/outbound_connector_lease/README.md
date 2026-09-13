# Connector-native outbound seam lease

This package solves one narrow fleet problem: two connector workers can both read
"not sent" and cross an external provider boundary before either send is visible
to the other. The mutex must therefore be an atomic mutation that workers can
actually execute **before** Gmail/Slack/provider send.

The practical connector boundary is a deterministic GitHub branch in
`woahwhattheheck/commons`:

```text
outbound-connector-lease/v1/<sha256(canonical seam JSON)>
```

`key.py` only compiles that branch name. It never authorizes a send and performs
no network call. The decisive mutex event is the GitHub **create branch** result:

- exact create success: this worker acquired the seam prerequisite;
- `422 Reference already exists`: another worker/history owns it -> HOLD;
- timeout, permission error, transport error, or any indeterminate result -> HOLD.

Do not convert an ambiguous create into success by reading the branch afterward:
another worker may have created the same branch during the ambiguity window.

## Canonical seam

Every seam contains an organization primary domain (`buyer_scope`) and one of
three **closed opportunity shapes**. Callers do not supply a free-form composite
opportunity string, so price/contact/route fields cannot be smuggled into the
hash schema.

### External opportunity

Use when an authoritative issuer/source has a durable procurement, project, or
issue ID:

```json
{
  "kind": "external",
  "authority": "issuer.example",
  "id": "rfp-04254"
}
```

`authority` is the source/issuer domain, not the contacted person's mailbox.
`id` is the stable external identifier. A changed recipient, prime contact,
quoted price, draft, or route keeps the same triple: buyer organization + source
authority + source ID.

### Cold outreach

Use exactly:

```json
{"kind":"cold"}
```

for unsolicited organization-level outreach with no durable external
opportunity. This intentionally permits only one cold seam per organization
until a real human/provider event creates a new state.

### Human reply event

Use one durable inbound provider event:

```json
{
  "kind": "reply",
  "provider": "gmail",
  "event_id": "<provider-message-id>"
}
```

This lets multiple workers race to answer a new human message while only one can
own that exact event. Automatic OOO/redirect messages do **not** become a new
reply opportunity; stay on the original external/cold seam.

## Required send sequence

1. Re-read provider truth and current coordination state.
2. Compile the canonical seam with `key.py`.
3. Atomically create that exact branch from current `main` through the connected
   GitHub provider.
4. If and only if the create itself succeeds, post the lease receipt/TAKE.
5. Re-read provider truth immediately before send. A historical/legacy send may
   predate the lease; if so, HOLD despite owning the branch.
6. Apply all normal owner/content/legal/payment/cooldown gates. The branch is
   mutual exclusion only.
7. Perform exactly one provider mutation.
8. Record the provider's canonical SENT/message receipt immediately and mark the
   seam DNR until a new human/provider event.
9. If the provider result is ambiguous, do not retry. Reconcile outcome only.

Branches are permanent one-touch state. Recovery from an abandoned lease
requires an explicit owner/fleet override tied to the original seam; workers
must not mint `v2`, alter source authority/ID, or switch contacts to evade it.

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

One human reply event:

```bash
python -m revenue.outbound_connector_lease.key \
  --buyer-scope example.com \
  --reply-provider gmail \
  --reply-event-id 1abc234
```

## Validation

```bash
python -m py_compile revenue/outbound_connector_lease/key.py
python -m unittest -v revenue.outbound_connector_lease.test_key
python -O -m unittest -v revenue.outbound_connector_lease.test_key
```

The helper rejects URLs/emails as organization/source domains, normalizes domain
case/trailing dot/IDNA, rejects duplicate/non-finite JSON, uses exact field sets
for each opportunity kind, and rejects price/contact/route/draft/subject fields
inside the external-opportunity schema. Determining the organization's actual
primary domain and the authoritative source ID is still a workflow evidence task;
the `outbound-send` skill requires provider/source readback before acquisition.
