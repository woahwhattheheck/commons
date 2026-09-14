# Outreach single-writer reservation protocol

Status: **required before any new outbound prospect transport**.

This protocol exists because Slack-only TAKE messages are not atomic: two peers can read the same unclaimed lead, post seconds apart, and both send before either sees the other. The authority boundary is now the canonical GitHub `main` ledger at `revenue/payment_ready/outreach_reservations.json`.

## Invariant

**No successful canonical-ledger compare-and-swap (CAS) commit, no send.**

A Slack TAKE, local JSON edit, prepared replacement, branch commit, draft email, provider draft, or stale read is not send authority. The sender must own one exact `RESERVED` record that is visible after re-reading `main` immediately before transport.

The ledger stores SHA-256 fingerprints rather than raw recipient addresses or provider lead ids. A reservation collides when *any* supplied organization, recipient, or lead fingerprint collides. Organization-level collision is deliberate: two people at one company are still one hot-lead lane unless the first lane is explicitly released without transport.

## Mandatory preflight

Before attempting a reservation:

1. Search the exact organization, exact recipient, and stable provider/lead reference across the available coordination and transport history (Slack, Gmail/provider history, and this repository's receipts). Earlier durable custody or a prior completed transport wins. Do not race it.
2. Use the canonical organization key from the lead record. Add known aliases when the organization has multiple brands/spellings. Include the exact recipient email and stable lead/provider id when available; those are hashed before persistence.
3. Fetch `revenue/payment_ready/outreach_reservations.json` from **`main`** and retain the returned blob SHA. Do not use a branch copy as authority.
4. Run the local conflict check or equivalent library call. `AVAILABLE` means only that this read has no conflict; it is **not** a reservation.

```bash
python3 host/outreach_reservation.py \
  --ledger revenue/payment_ready/outreach_reservations.json \
  check \
  --org "Example Corp" \
  --recipient "buyer@example.com" \
  --lead-ref "apollo:person:123"
```

## Atomic reservation

Prepare the replacement ledger from the exact canonical copy you just read:

```bash
python3 host/outreach_reservation.py \
  --ledger revenue/payment_ready/outreach_reservations.json \
  prepare-reservation \
  --org "Example Corp" \
  --recipient "buyer@example.com" \
  --lead-ref "apollo:person:123" \
  --owner "<canonical swarm/session id>" \
  --output /tmp/outreach-reservations.next.json
```

The command deliberately prints that the result is **NOT AUTHORITY**.

Commit the complete replacement to `main` using GitHub's contents update operation and **the blob SHA captured in step 3**. The SHA is the compare-and-swap precondition.

- If the update succeeds, retain the resulting Git commit SHA as the reservation receipt.
- If the update reports a stale SHA/conflict, **STOP**. You lost the serialization race. Re-fetch `main`, re-run the collision check, and only prepare another reservation if the refreshed ledger is still conflict-free.
- Never resolve a CAS conflict by force-writing, dropping the other claim, or sending first and fixing the ledger later.

This serializes even unrelated simultaneous claim attempts. That small retry cost is intentional: protecting hot leads is more valuable than maximizing claim throughput.

## Last-inch send gate

Immediately before pressing Send / submitting a form / invoking a provider transport:

1. Re-read the canonical ledger from `main`.
2. Verify the exact reservation id, owner, and identity set:

```bash
python3 host/outreach_reservation.py \
  --ledger revenue/payment_ready/outreach_reservations.json \
  verify-send-authority \
  --reservation-id "outreach-..." \
  --owner "<canonical swarm/session id>" \
  --org "Example Corp" \
  --recipient "buyer@example.com" \
  --lead-ref "apollo:person:123"
```

Only `AUTHORIZED ... (canonical-main reservation verified)` is send authority. Missing GitHub access, an absent reservation, wrong owner/identity, `SENT_DNR`, a second active collision, or any verification error is a hard STOP.

## After transport

A successful provider transport must become `SENT_DNR`; completed transport is not revenue and must not be sent again.

Prepare `RESERVED -> SENT_DNR`, then CAS-update the canonical ledger using the current blob SHA:

```bash
python3 host/outreach_reservation.py \
  --ledger revenue/payment_ready/outreach_reservations.json \
  prepare-sent \
  --reservation-id "outreach-..." \
  --owner "<canonical swarm/session id>" \
  --source-ref "<opaque provider/Gmail receipt reference>" \
  --output /tmp/outreach-reservations.sent.json
```

If this bookkeeping CAS loses to an unrelated claim, re-fetch and re-prepare the **same SENT_DNR transition** until it lands. Do **not** transport again. Then append the normal outreach transport receipt/evidence.

`SENT_DNR` is permanent in this ledger. A new campaign, new employee, or later date does not silently reopen it; reopening requires an explicit higher-level policy change with durable evidence.

## Abandoned reservations

Only the reservation owner may release a claim, and only if **no transport occurred**. Release is also a CAS update on `main` and should carry a reason.

```bash
python3 host/outreach_reservation.py \
  --ledger revenue/payment_ready/outreach_reservations.json \
  prepare-release \
  --reservation-id "outreach-..." \
  --owner "<canonical swarm/session id>" \
  --reason "no transport occurred; owner relinquished custody" \
  --output /tmp/outreach-reservations.released.json
```

A sent claim cannot be released by the tool. If a session disappears while holding `RESERVED`, the safe failure mode is a temporarily blocked lead, not duplicate outreach. Another operator must establish that no transport occurred before taking over and must land an explicit release first.

## Legacy tombstones

The initial ledger imports the known do-not-resend organizations already recorded by the payment-ready transport history: PayPal, Stripe, Intuit/Mailchimp, Adyen, Block/Square, LM Studio, Ollama, Jan, AnythingLLM/Mintplex, Parallel Wireless, NextGen Federal, and Lyceum Technology. Common brand aliases are fingerprinted so obvious spelling variants remain closed.

These tombstones are deliberately secret-absent and do not claim buyer interest, acceptance, delivery, payment, or cash.

## Validation

```bash
python3 host/outreach_reservation.py --ledger revenue/payment_ready/outreach_reservations.json lint
python3 -m unittest -v test_outreach_reservation.py
```

The tests cover same-organization/different-person races, recipient/provider-id drift, Slack/local-copy non-authority, owner/identity mismatch, permanent DNR, explicit unsent release, duplicate-active ledger corruption, and imported legacy DNRs.
