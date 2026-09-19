# Outreach Qualification Firewall

`p/outreach-qualification-firewall` is a deterministic **pre-send decision firewall** for paid outreach lanes. It separates:

1. whether an opportunity is sufficiently evidenced for owner review; and
2. whether this exact session currently holds matching single-writer transport authority for the same canonical outreach intent.

The package never sends email, Slack, forms, portal submissions, proposals, contracts, invoices, or payments. `authorized_to_send=true` is only a bounded precondition result. It is not proof of buyer interest, acceptance, award, payment, cash, or revenue.

## V2 trust roots

V2 removes caller-selected organization/purpose spelling and caller-carried relationship state from the send-authority trust path.

Two host-retained HMAC authorities are used:

- `OUTREACH_CONTEXT_AUTHORITY_KEY_HEX` authenticates canonical outreach identity and relationship-head snapshots.
- `OUTREACH_WRITER_LEASE_AUTHORITY_KEY_HEX` authenticates the external single-writer lease.

Neither key is accepted from the packet. Both are loaded by the host process. The firewall does not mint either authority.

### Canonical identity binding

Every packet carries an authenticated `identity_binding` tied to the exact `source_packet_sha256` and `opportunity_id`. It maps the packet aliases `org_ref` and `purpose_ref` to authority-issued `canonical_org_id` and `canonical_purpose_id`, with observation and validity bounds.

The semantic collision key is SHA-256 over canonical:

`opportunity_id × canonical_org_id × canonical_purpose_id`

Mailbox, form, contact name, route, and caller-selected alias spelling are deliberately excluded. Two agents discovering different contacts or spelling the same organization/purpose differently therefore converge when the context authority maps those aliases to the same canonical IDs. Genuinely distinct canonical purposes remain separate.

Missing, forged, expired, future, wrong-source, wrong-opportunity, or alias-mismatched identity authority fails closed.

### Relationship-head binding

The contact record carries an authenticated relationship snapshot that binds:

- exact source packet generation and opportunity;
- canonical organization and purpose;
- contact and route;
- relationship state and evidence;
- relationship generation and exact head SHA-256;
- observation and validity timestamps.

`DNR`, `BOUNCE`, and `SENT_DNR` block qualification. A relationship snapshot older than the current freshness ceiling also blocks qualification.

For a **current** send authorization, the authenticated relationship snapshot must have been observed at or after the winning writer lease was issued. A fresh `GO` therefore cannot authorize against an older cached `OPEN` snapshot. This creates an explicit ordering fence between the relationship census and the exact writer election used for the attempted send.

The current maximum relationship age is 60 seconds; a signed snapshot may additionally carry a shorter validity window.

## Host-interpreter trust boundary

This package is a **data/evidence firewall inside a trusted Python interpreter**. It is not a sandbox for malicious Python code already executing in that same interpreter.

Supported adversarial inputs include forged/stale packets, forged tags, stale relationship state, alias variation, replay, schema/type abuse, duplicate JSON keys, and ordinary post-import rebinding or mutation of module globals / function defaults / keyword defaults. The implementation deliberately captures those dependency generations so accidental or ordinary monkeypatching does not silently redefine send-gating semantics.

The following are explicitly **outside this package's trust boundary**:

- direct reflective mutation of live function internals such as `__closure__[...].cell_contents` or `__code__`;
- debugger/frame/GC/ctypes-style mutation of the validator's live Python object graph;
- arbitrary untrusted plugin/agent code running with interpreter-level access to the validator process.

CPython makes closure cells and function internals writable to code already inside the process. A Python library cannot truthfully claim isolation from an attacker that can rewrite the library's executing trust objects. If that attacker exists, treat the host interpreter as compromised.

Operational rule: **do not colocate untrusted agent/plugin code with this validator when `authorized_to_send` is consequential.** Untrusted seats must cross a separately isolated and authenticated process/provider boundary; this package may then validate the data received at that boundary. The HMAC keys and process clock are only meaningful while the validator interpreter itself is trusted.

The retained hostile suite intentionally demonstrates the closure-cell clock/HMAC bypasses under this declared out-of-scope condition. Those tests are boundary proofs, not claims that reflective interpreter tamper is blocked.

## Opportunity and economics gates

A packet also binds:

- exact opportunity/source generation and SHA-256;
- absolute deadline plus minimum required runway;
- submission route and registration/onboarding state;
- explicit qualification gates (`SATISFIED | UNSATISFIED | UNKNOWN`), with `UNKNOWN` failing closed for outreach-required gates;
- a non-zero bounded paid workshare: currency, integer minor-unit value, compensation basis, quantity ceiling, and scope reference;
- requesting seat and session nonce.

A registration-required lane must be `READY`. Runway passes only when `deadline - evaluated_at >= min_runway_seconds`.

## Single-writer send authority

Historical evaluation is intentionally non-authorizing even when all other evidence is positive.

Only `current` evaluation can set `authorized_to_send=true`, and only when:

- owner-review gates pass;
- canonical identity authority is valid and current;
- relationship-head authority is valid, current, non-blocking, and fresh enough;
- relationship observation is not older than the selected writer lease;
- lease status is exactly `GO` (bare `SELECTED` is not enough);
- lease collision key, seat, and session nonce match;
- process UTC is inside the lease interval;
- lease lifetime is no more than one hour.

A missing lease produces `HOLD_WRITER_LEASE_MISSING`; it is not a parse error.

The firewall does not elect, consume, mint, or refresh the lease. The external Muse/OneWriter-style system remains the authority that produces the unique authenticated `GO`.

## Strict ingress and retained receipts

JSON ingress rejects duplicate keys, floating/non-finite numbers, oversized input, unsafe Unicode, malformed canonical routes/timestamps, bool-as-int aliases in bounded numeric fields, and schema drift.

Decision receipts bind the normalized packet digest, exact source generation, canonical dedupe key, qualification/send states, hold reasons, evaluation mode/time, and a hard-false authority ceiling. Verification re-evaluates semantics and, for a current positive receipt, re-checks against fresh process time.

Trust-bearing canonicalization, writer-message generation, context verification, dedupe, current-clock, and verifier helpers capture their intended dependency generation rather than accepting ordinary post-import module-global/default substitution. This is resilience to ordinary monkeypatching, not a sandbox boundary against direct reflective mutation of live Python function internals; see the host-interpreter trust boundary above.

## CLI

```bash
python p/outreach-qualification-firewall/cli.py historical p/outreach-qualification-firewall/demo.json --as-of 2026-09-17T20:00:00Z
python p/outreach-qualification-firewall/cli.py current p/outreach-qualification-firewall/demo.json
python -m unittest discover -v p/outreach-qualification-firewall -p 'test_*.py'
python -O -m unittest discover -v p/outreach-qualification-firewall -p 'test_*.py'
```

The retained demo is synthetic. Current execution may legitimately HOLD when its time-bounded lease or relationship snapshot is stale.

## Authority ceiling

Always false in the receipt:

- package performs send;
- buyer qualified or interested;
- submission authorized;
- signature or contract authority;
- award or payment authority;
- cash or revenue authority.

Source digests provide retained-packet integrity, not independent buyer authenticity. The HMAC context authority provides canonical identity/relationship assertions for this firewall; it does not itself prove buyer interest, contract formation, payment, or revenue.
