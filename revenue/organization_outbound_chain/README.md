# Mandatory organization-aware outbound chain

Issue: `woahwhattheheck/commons#14269`.

This package closes the repository-level composition gap that allowed different workers to contact different people at the same hot organization seconds apart. It is **not another mutex**. It composes the already-landed controls in one provider-bound path:

`current organization-pressure receipt -> exact active organization lease + private holder capability -> exact opportunity/prospect/route commitments -> action-specific initial-outreach slot -> terminal outbound_send_consumer -> retained organization terminal outcome`

## Authority law

A positive prerequisite never means “send authorized” or “send completed.” The chain receipt always keeps `external_send_authorized=false`, `replay_or_retry_authorized=false`, and `payment_or_revenue_inferred=false`. Raw route/prospect bytes and holder capabilities are never copied into durable receipts.

The organization lease must be the exact active bytes **and** exact store generation, and its `holderCapabilityCommitment` must match the private 32-byte capability supplied by the host. The current organization-pressure receipt is reverified through the fixed production verifier and must match the lease's retained `pressureReceiptSha256`, `authorityCommitment`, and `ledgerCommitment`.

The lease's `prospectFingerprint`, `routeCommitment`, and `opportunityCommitment` must be created with this package's exported commitment helpers. Those helpers domain-separate and hash host-retained canonical identities; the raw identities never become public coordination evidence.

Initial outreach then runs the landed canonical one-shot opportunity slot. Inside that callback, the terminal consumer re-probes the full live authority immediately before the provider callback. The actual provider function is called only by `revenue.outbound_send_consumer.consume_once`. Timeout/exception/uncertain persistence burns that terminal seam and returns reconciliation-only; the chain never retries automatically.

## Provider registry

Supported initial-outreach adapters are `gmail`, `slack_dm`, `discord`, and `webhook_mail`. They are thin wrappers in `adapters.py`; none invokes a provider directly.

`registry.find_bypasses()` is the CI coverage fence. It rejects repository source that directly calls the lower initial-outreach primitive or terminal consumer outside this chain, and it rejects known concrete provider-send APIs outside the registered adapter surface. Future providers must add a guarded adapter and registry marker in the same change.

## Development safety

The tests use fakes/mocks only. No Gmail, Slack, Discord, webhook, customer, payment, or revenue provider is contacted in development or CI.
