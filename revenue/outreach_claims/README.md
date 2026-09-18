# Atomic outreach leases

This is the shared single-writer primitive for outbound contact. It replaces
human/bot arbitration as the collision-control mechanism; it does **not**
replace the canonical Airtable CRM, `lm_gtm_index`, Gmail truth, or provider
receipts.

## Why this exists

`lm_gtm_index.py claim` is useful occupancy metadata, but its local
read/append/rewrite flow is not a cross-process compare-and-swap. Two agents
starting from the same snapshot can both believe they acquired a row.

An outreach lease uses one deterministic, public-safe GitHub path per private
route. The raw email/address/URL is never written to Git. GitHub Contents
writes supply the race primitive:

1. Compute the path locally:

   ```sh
   python3 host/outreach_claim.py key 'private-route@example.com'
   ```

2. Render an ACTIVE record locally:

   ```sh
   python3 host/outreach_claim.py new 'private-route@example.com' \
     --claimant Z-SOL-17 --purpose 'one paid fixed-scope message'
   ```

3. `create_file` that exact path on current `main`.
   - create succeeds -> you own the lease;
   - path already exists -> you lost the first-writer race; fetch it before
     doing anything else.

4. Every later transition is compare-and-swap:
   - fetch the file and its blob SHA;
   - generate the next record locally (`consume`, `release`, `reclaim`, or
     evidence-backed `reopen`);
   - `update_file` the same path **with that exact fetched SHA**.
   A stale writer loses instead of silently overwriting a newer claim.

5. Immediately before transport, the owner must `consume` the ACTIVE lease and
   land that CAS update first. `CONSUMED` is terminal for unsolicited outbound:
   no second send on silence. A new generation from `CONSUMED` requires
   `reopen --evidence ...`, intended for a genuine inbound/provider event. The
   evidence value itself is hashed and not stored.

## State machine

`ACTIVE -> CONSUMED` — burn the single-send right before transport.

`ACTIVE -> RELEASED -> ACTIVE` — owner abandons; another agent may reclaim.

`ACTIVE -> EXPIRED -> ACTIVE` — TTL elapsed; another agent may reclaim.

`CONSUMED -> ACTIVE` — only `reopen` with a non-empty new-evidence pointer.

There is no `--steal`. If another agent owns a live lease, pick different work.
Default TTL is 30 minutes; supported range is 1-240 minutes.

## Privacy

The lease file stores only SHA-256 digests plus claimant/timestamps/status.
It does not store the raw target route, purpose text, or evidence text. Peers
who independently know the same route compute the same path and collide safely
without publishing the prospect address.

## Cross-harness rule

A Slack `TAKE`, Muse decision, local file, draft, or in-memory claim is not the
single-writer proof. The proof is the current-main lease object plus the blob
SHA used for the successful CAS transition.

If GitHub is unavailable, **do not substitute a non-atomic send**. Build and
research work can continue; outbound waits until one shared write road can
establish the lease.

## Commands

```sh
python3 host/outreach_claim.py key ROUTE
python3 host/outreach_claim.py new ROUTE --claimant YOU --purpose PURPOSE
python3 host/outreach_claim.py inspect lease.json
python3 host/outreach_claim.py consume lease.json --claimant YOU
python3 host/outreach_claim.py release lease.json --claimant YOU
python3 host/outreach_claim.py reclaim lease.json --claimant YOU
python3 host/outreach_claim.py reopen lease.json --claimant YOU --evidence SOURCE_POINTER
python3 -m unittest -v tests/test_outreach_claim.py
```

The CLI deliberately does not send email or mutate GitHub. Each harness uses
its already-available GitHub write road for the CAS step; the record helper
keeps normalization/state identical across harnesses.
