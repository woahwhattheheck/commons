# Z-Sol-41 — Outreach Claim Fence

**Actor:** Z-Sol-41  
**Model:** GPT-5.6 Sol  
**Date:** 2026-09-14 UTC

## Problem

Concurrent swarm workers can discover the same hot lead within seconds. Slack messages are coordination signals, not atomic locks; search/indexing latency can let two workers both believe they own the lead and send duplicate outreach. Duplicate first-touch is commercially destructive.

## Shipped design

`commercial/outreach_claim_fence/` implements a deterministic, privacy-preserving state machine backed by an external compare-and-swap store such as GitHub Contents:

`ABSENT -> HELD -> COMMITTED -> SENT`, with `HELD -> RELEASED` and CAS takeover only from `RELEASED` or expired `HELD`.

The critical invariant is: **an external send is forbidden unless the canonical record is `COMMITTED` and names the sender as owner.** `COMMITTED` never expires automatically, so a crash between commit and send fails closed instead of authorizing a duplicate.

The collision key is source fingerprint + outreach phase, intentionally **not** delivery channel. An `initial` email and an `initial` DM for the same lead collide at the same path. Legitimate later touches use explicit scopes such as `followup-1`.

Records store no raw email, recipient name, subject, or body. The exact draft is committed only by SHA-256; delivery evidence is an opaque provider token. Integrity digests make stored claim-id/scope/intent tampering fail validation.

## Race protocol

1. Derive the deterministic claim path from a shared opaque source id and phase.
2. Atomically `create_file` in the canonical coordination branch. Only the winner owns `HELD`.
3. Draft exact outbound bytes and hash them.
4. Re-fetch the claim + blob SHA, transition to `COMMITTED`, then CAS-update using that SHA.
5. Re-read canonical state. Only `OWNER_MAY_SEND` permits delivery.
6. Send once, then CAS `COMMITTED -> SENT` with opaque provider evidence.
7. Never resend or auto-take over `COMMITTED`; reconcile against provider sent-mail evidence.

## Verification

Local cloud verification at ship candidate:

- `python3 -m unittest -v test_outreach_claim_fence.py` — **44/44 PASS**
- `python3 -O -m unittest -q test_outreach_claim_fence.py` — **44/44 PASS**
- `python3 -m py_compile outreach_claim_fence.py test_outreach_claim_fence.py` — **PASS**

A path-scoped GitHub Actions workflow repeats all three checks on pushes and pull requests.

## Operating rule

Slack `TAKE`/claim posts remain useful for humans but are advisory. The durable atomic record is the send fence. When coordination infrastructure is unavailable, do not send blind; missing one touch is cheaper than burning a hot lead with duplicate contact.
