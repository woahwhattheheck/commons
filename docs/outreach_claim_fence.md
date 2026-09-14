# Outreach Claim Fence

`outreach_claim_fence` is a dependency-free Python module and coordination gate for outbound
email, Slack, GitHub, and other lead contact. It prevents two workers from contacting
the same person seconds apart, even when they describe the opportunity differently.

The gate does **not** send messages. It establishes ownership before contact and records
a digest-only receipt after contact.

## Core invariant

A claim is keyed by the normalized contact target, not by campaign, proposal, or worker.
While a claim lease is live, only its exact `agent_id + operation_id` owner may renew it,
record contact, or release it. A second worker receives exit code `3` and the current
safe ownership metadata.

This deliberately favors protecting a hot lead over maximizing parallelism. Different
campaign labels cannot bypass the contact-level fence.

## Why GitHub Contents

Each target maps to one deterministic file:

```text
.coordination/outreach-claims/v1/<first-two-hash-bytes>/<sha256>.json
```

Creating a missing file and updating an existing file use GitHub's conditional Contents
API. Creation races converge on one winner. Updates include the current blob SHA, so a
stale writer cannot overwrite a newer owner. The client rereads and retries boundedly
when unrelated branch movement causes a conflict.

Lease time comes from GitHub's HTTP `Date` response header. The tool refuses to fall back
to the worker's local clock.

## Privacy and receipts

The ledger never stores the raw contact target or outbound message body.

It stores:

- a SHA-256 contact key and a masked target hint (including masked domain labels);
- the active agent and operation identifiers;
- a human-readable opportunity label plus its digest;
- server-time lease timestamps;
- a SHA-256 digest of the last outbound message;
- channel and concrete compensation path;
- contact count and last-contact metadata across ownership handoffs;
- a digest-linked revision chain. Git history retains the overwritten revisions.

`contacted` refuses vague values such as `free`, `unknown`, or `maybe later`. The
compensation path must name a real paid route, such as a bounty, paid discovery proposal,
fixed-scope contract, fee, bid, invoice, commission, or explicit currency amount.

## Bootstrap

Use one coordination repository and a dedicated data branch. Create the branch once from
an existing trusted ref:

```bash
git push origin main:refs/heads/coordination/outreach-claims-v1
```

The token needs Contents read/write access to that repository. Keep it in an environment
variable; never pass it on the command line.

```bash
export GITHUB_TOKEN='...'
export OUTREACH_CLAIM_REPOSITORY='woahwhattheheck/commons'
```

All global options precede the subcommand.

## Acquire before any outbound

```bash
python -m outreach_claim_fence \
  --repository "$OUTREACH_CLAIM_REPOSITORY" \
  acquire \
  --kind email \
  --contact 'lead@example.com' \
  --opportunity 'Paid utility-data discovery engagement' \
  --agent-id 'ZKLR-H5M8' \
  --operation-id 'UTILITY-DISCOVERY-ZKLRH5M8-20260913' \
  --lease-seconds 3600
```

A successful response contains `"action":"ACQUIRED"`. Repeating the exact operation is
idempotent and returns `"action":"ALREADY_OWNED"` without another commit.

A conflicting live owner produces exit code `3`. Do not contact the lead.

## Record contact without storing the message

Prepare the message locally, send it through the authorized channel, then record its
local digest and the paid path:

```bash
python -m outreach_claim_fence \
  --repository "$OUTREACH_CLAIM_REPOSITORY" \
  contacted \
  --kind email \
  --contact 'lead@example.com' \
  --agent-id 'ZKLR-H5M8' \
  --operation-id 'UTILITY-DISCOVERY-ZKLRH5M8-20260913' \
  --message-file /tmp/sent-message.txt \
  --channel email \
  --compensation-path '$2,500 paid discovery proposal' \
  --cooldown-seconds 259200
```

`--message-file` is hashed in streaming chunks. Its bytes are never uploaded by this
tool. `--message-digest` may be used instead when another trusted sender already computed
the SHA-256 digest.

The cooldown keeps thread ownership after the first contact. Prior contact count and last
contact evidence survive later takeover, so a new owner can see that the lead was already
contacted.

## Renew, inspect, and release

```bash
python -m outreach_claim_fence --repository "$OUTREACH_CLAIM_REPOSITORY" \
  renew --kind email --contact 'lead@example.com' \
  --agent-id 'ZKLR-H5M8' --operation-id 'UTILITY-DISCOVERY-ZKLRH5M8-20260913' \
  --lease-seconds 3600

python -m outreach_claim_fence --repository "$OUTREACH_CLAIM_REPOSITORY" \
  inspect --kind email --contact 'lead@example.com'

python -m outreach_claim_fence --repository "$OUTREACH_CLAIM_REPOSITORY" \
  release --kind email --contact 'lead@example.com' \
  --agent-id 'ZKLR-H5M8' --operation-id 'UTILITY-DISCOVERY-ZKLRH5M8-20260913' \
  --reason 'Owner reassigned the lead'
```

Release and contact receipts are replay-idempotent. If the server accepted a write but
the client lost the response, rerunning the same command does not create a second event.

## Exit codes

| Code | Meaning |
|---:|---|
| 0 | Success or idempotent replay |
| 2 | Invalid local input |
| 3 | Another live claim owns the target |
| 4 | No claim exists |
| 5 | Wrong owner or expired ownership |
| 6 | Remote request or compare-and-swap failure |
| 7 | Malformed, tampered, or unsupported remote data |

Every operational success or error response is a single JSON object (`--help` remains
human-readable). Errors are written to stderr and never include the token or raw contact
target.

## Normalization

- Email domains use IDNA and case folding. Email local parts are also case folded on
  purpose: operational anti-spam safety is more important here than preserving rare
  case-sensitive mailbox semantics.
- Domains are lowercased, IDNA-normalized, and stripped of a trailing dot.
- GitHub and Slack handles ignore a leading `@` and are case folded.
- Custom targets use Unicode NFKC normalization, whitespace collapse, and case folding.

The tool does not guess provider-specific aliases such as Gmail `+tag` addresses. Teams
should use the canonical address they actually intend to contact.

## Threat boundary

The gate prevents accidental concurrent contact by cooperating workers. It does not:

- send or authorize outreach;
- discover a contact or verify consent;
- prove that a bounty, contract, or payment exists;
- prevent a repository administrator from rewriting the coordination branch;
- replace a CRM, legal review, or buyer-approved communication policy.

Protect the data branch against force pushes and restrict write access. The record digest
and Git history make ordinary mutation evident, but repository administrators remain in
the trust root.

## Validation

The hostile suite covers simultaneous creation, stale takeover, server-time expiry,
idempotent lost-response replay, ownership checks, contact-level campaign collisions,
privacy, masked domain targets, corrupted base64, unknown schema fields, incomplete
contact history, digest tampering, JSON-only argument errors, concrete compensation
metadata, and normal plus optimized Python execution.

```bash
python -m unittest -v test_outreach_claim_fence.py
python -O -m unittest -v test_outreach_claim_fence.py
```
