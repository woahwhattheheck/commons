# Mandatory organization-aware outbound chain

Issue: `woahwhattheheck/commons#14269`.

This package closes the repository-level composition gap that allowed different workers to contact different people at the same hot organization seconds apart. It is **not another mutex**. It composes the already-landed controls in one provider-bound path:

`current organization-pressure receipt -> exact active organization lease + private holder capability -> exact opportunity/prospect/route commitments -> action-specific initial-outreach slot -> terminal outbound_send_consumer -> exact typed provider boundary -> retained organization terminal outcome`

## Authority law

A positive prerequisite never means “send authorized” or “send completed.” The chain receipt always keeps `external_send_authorized=false`, `replay_or_retry_authorized=false`, and `payment_or_revenue_inferred=false`. Raw route/prospect bytes and holder capabilities are never copied into durable receipts.

The organization lease must be the exact active bytes **and** exact store generation, and its `holderCapabilityCommitment` must match the private 32-byte capability supplied by the host. The current organization-pressure receipt is reverified through the fixed production verifier and must match the lease's retained `pressureReceiptSha256`, `authorityCommitment`, and `ledgerCommitment`.

The lease's `prospectFingerprint`, `routeCommitment`, and `opportunityCommitment` must be created with this package's exported commitment helpers. Those helpers domain-separate and hash host-retained canonical identities; the raw identities never become public coordination evidence.

Initial outreach then runs the landed canonical one-shot opportunity slot. Inside that callback, the terminal consumer re-probes the full live authority immediately before the provider boundary. The chain no longer accepts an arbitrary per-call provider callback: one exact frozen boundary class selects one registered transport method, and `revenue.outbound_send_consumer.consume_once` invokes that boundary at most once. Timeout/exception/uncertain persistence burns that terminal seam and returns reconciliation-only; the chain never retries automatically.

## Provider registry and host boundary

Supported initial-outreach adapters are `gmail`, `slack_dm`, `discord`, and `webhook_mail`. Each adapter fixes its provider and creates one exact boundary object; callers cannot smuggle a different provider name, callback, or boundary through adapter kwargs.

`registry.validate_registry()` proves the closed provider manifest maps to real adapter functions, boundary classes, and transport methods. `registry.find_bypasses()` then scans repository code for direct lower-primitive calls, import aliases/rebindings, dynamic literal `getattr` bypasses, registered transport methods outside the boundary, and known provider/host mutation identities across supported source extensions. Future providers must extend the manifest, typed boundary, adapter, and coverage proof in the same change.

The current ChatGPT host mutation identities are inventoried explicitly, including Gmail `mcp__Gmail__send_email` / `send_draft` / `forward_emails` and Slack `mcp__Slack__slack_send_message` / `slack_schedule_message`. Discord and webhook-mail identities are likewise retained in the registry. This is an integration contract, not a false sandbox claim: repository CI can prevent repository code from bypassing the registered boundary, but it cannot intercept an out-of-process connector call made by an agent that never enters repository code. Host/runtime policy (including Muse single-writer adjudication) must bind those exact execution identities to this same organization-aware decision before external mutation.

## Development safety

The tests use fakes/mocks and local atomic stores only. No Gmail, Slack, Discord, webhook, customer, payment, or revenue provider is contacted in development or CI.
