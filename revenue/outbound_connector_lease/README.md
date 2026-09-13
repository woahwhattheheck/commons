# Connector-native outbound seam lease

This package solves one narrow fleet problem: two connector workers can both read
"not sent" and cross an external provider boundary before either send is visible
to the other. The mutex must therefore be an atomic mutation that the workers
can actually execute **before** Gmail/Slack/provider send.

The practical connector boundary is a deterministic GitHub branch in
`woahwhattheheck/commons`:

```text
outbound-connector-lease/v1/<sha256(canonical seam JSON)>
```

`key.py` only compiles that branch name. It never authorizes a send and performs
no network call. The authority event is the GitHub **create branch** response:

- exact create success: this worker acquired the seam prerequisite;
- `422 Reference already exists`: another worker/history owns it -> HOLD;
- timeout, permission error, transport error, or any indeterminate result -> HOLD.

Do not convert an ambiguous create into success by reading the branch afterward:
another worker may have created the same branch during the ambiguity window.

## Canonical seam

The seam is `buyer_scope + opportunity_scope`.

`buyer_scope` is the organization's primary domain, never an individual email.
This deliberately makes multiple contacts at one organization collide.

`opportunity_scope` is one durable semantic opportunity identifier chosen before
send:

1. Prefer an externally authoritative procurement/project/issue ID, normalized
   into a stable machine token (for example `uw-rfi-1255311` or `rfp-04254`).
2. For unsolicited outreach with no durable external opportunity, use exactly
   `cold`. This makes the first cold touch own the organization-level cold seam.
3. For a human reply that should be answered once, use the durable inbound event
   identity such as `reply:<provider-message-id>`.
4. If an internal opportunity key already existed before outreach, reuse it
   exactly. Never mint a synonym to evade an existing lease.

**Never** put recipient/person, route, quoted price, `$5k` vs `$7.5k`, subject,
draft version, alternate mailbox, or scope revision in the opportunity key.
Those are precisely the aliases that previously let materially same outreach
race through different lanes.

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

Branches are permanent one-touch state. A changed price, alternate recipient, or
new draft is not a new opportunity. Recovery from an abandoned lease requires an
explicit owner/fleet override tied to the original seam; workers must not mint
`v2`, a new spelling, or a route-specific key on their own.

## Validation

```bash
python -m py_compile revenue/outbound_connector_lease/key.py
python -m unittest -v revenue.outbound_connector_lease.test_key
python -O -m unittest -v revenue.outbound_connector_lease.test_key
```

The helper rejects URLs/emails as buyer scope, normalizes domain case/trailing
dot/IDNA, rejects duplicate/non-finite JSON, and produces deterministic branch
keys. Semantic alias prevention is a workflow contract, not something a hash
function can infer; the `outbound-send` skill defines that boundary.
