# Outreach Qualification Firewall

`p/outreach-qualification-firewall` is a deterministic **pre-send decision firewall** for paid outreach lanes. It separates two questions that the swarm has repeatedly conflated:

1. **Is this opportunity sufficiently evidenced for owner review?**
2. **Does this exact session currently hold matching single-writer transport authority?**

The package never sends email, Slack, forms, portal submissions, proposals, or payments. `authorized_to_send=true` is only a bounded precondition result. It is not proof of buyer interest, acceptance, contract, award, payment, cash, or revenue.

## Fail-closed contract

A packet binds:

- exact opportunity/source generation and SHA-256;
- absolute deadline plus minimum required runway;
- submission route and registration/onboarding state;
- explicit qualification gates (`SATISFIED | UNSATISFIED | UNKNOWN`), with `UNKNOWN` failing closed for outreach-required gates;
- a non-zero bounded paid workshare (currency, integer minor-unit value, compensation basis, quantity ceiling, scope reference);
- exact organization/contact/route/purpose relationship state;
- requesting seat + session nonce;
- an external writer-lease receipt bound to the deterministic collision key.

`DNR`, `BOUNCE`, and `SENT_DNR` block owner qualification. A registration-required lane must be `READY`. Runway is accepted only when `deadline - evaluated_at >= min_runway_seconds`.

## Send authority

Historical evaluation is intentionally non-authorizing even if all evidence and lease fields are positive. Only `current` evaluation can set `authorized_to_send=true`, and only when:

- all owner-review gates pass;
- lease status is exactly `GO` (bare `SELECTED` is not enough);
- collision key, seat, and session nonce match;
- process UTC is inside the lease interval;
- the lease lifetime is no more than one hour, preventing indefinitely reusable `GO` receipts.

A missing lease produces `HOLD_WRITER_LEASE_MISSING`; it is not a parse error. The firewall does **not** mint or consume a lease. It expects a unique `GO` from the external single-writer/atomic-consume system. It also does not perform the provider mutation after a positive result.

## Dedupe identity

The collision key is SHA-256 over canonical:

`opportunity_id × org_ref × purpose_ref`

The key intentionally excludes mailbox/form/contact identity. Materially identical outreach to the same organization for the same opportunity/purpose therefore converges even when different agents discover different routes or named contacts. Route identity is still retained and validated in the packet; it simply cannot be used to evade the semantic collision fence.

## CLI

```bash
python p/outreach-qualification-firewall/cli.py historical p/outreach-qualification-firewall/demo.json --as-of 2026-09-17T20:00:00Z
python p/outreach-qualification-firewall/cli.py current p/outreach-qualification-firewall/demo.json
python -m unittest discover -v p/outreach-qualification-firewall -p 'test_*.py'
python -O -m unittest discover -v p/outreach-qualification-firewall -p 'test_*.py'
```

The demo is synthetic and its lease is intentionally time-bounded. A later `current` run may therefore return a stale-lease HOLD; that is expected behavior, not a real buyer, lead, or authorization.

## Authority ceiling

Always false in the receipt: package performs send, buyer qualification/interest, submission authority, signature/contract authority, award/payment authority, and cash/revenue authority.

Source digests provide retained-packet integrity, not independent authenticity. A downstream caller must obtain the packet from its source-authority process; changing source facts without the bound digest is rejected, but this package does not authenticate the external buyer/source by itself.
