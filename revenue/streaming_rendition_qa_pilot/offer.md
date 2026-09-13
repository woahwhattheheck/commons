# Streaming Rendition QA Pilot

`STREAMING-RENDITION-QA-PILOT-KIT-ZLCV7Q3-20260913`

A fixed-scope, **metadata-only** pre-release diagnostic for teams operating multi-rendition live or VOD streaming workflows. It is designed to find release-blocking inconsistencies in sanitized manifest/export data before a stream or asset is published.

## Pilot A — $2,500 metadata-only diagnostic

Pilot-test price: **$2,500 flat**. This is an explicit test price, not a claim about prevailing market rates.

Buyer supplies one sanitized metadata export covering **no more than 250 assets**. The export may contain rendition declarations, codec/profile metadata, segment timing, caption/audio language metadata, DRM *reference IDs*, artifact digests, publication windows, and CDN region identifiers.

We deliver:

- deterministic READY/HOLD evaluation against the seven currently proven fault classes;
- a synthetic-to-buyer mapping showing which checks fired and why;
- an evidence receipt with input/output hashes and stable reason codes;
- a prioritized findings table suitable for an engineering handoff;
- one review session focused on findings and whether a paid integration is justified.

Acceptance: the diagnostic is complete when the agreed sanitized export has been evaluated, the deterministic findings packet and receipt have been delivered, and any unsupported fields are explicitly reported instead of silently ignored.

## Pilot B — $7,500 integration sprint

Pilot-test price: **$7,500 flat**, offered only after a paid diagnostic proves value and one bounded adapter surface is agreed.

The sprint may add one agreed metadata-export adapter, one CI or pre-release invocation path, deterministic receipts, and a runbook/handoff. It does **not** include open-ended custom integrations, provider-side mutation, or media processing.

Acceptance: the agreed adapter deterministically emits the validated schema, the pre-release invocation reproduces the same result projection for the acceptance fixture, hostile inputs fail closed, and the buyer receives the runbook and evidence receipt.

## Hard boundary

No media bytes are required. No DRM keys or secrets. No content editing, transcoding, CDN mutation, publishing, rights determination, release decision, customer/provider credential use, contract signature, payment action, or production mutation is authorized by this packet. `RELEASE_READY` means only that supplied metadata is internally consistent; media operations retain release authority.

## Stop rule

Do not sell an integration sprint merely to keep work moving. Stop if the buyer cannot provide a sanitized metadata export without disproportionate procurement/security overhead, or if the buyer can already demonstrate equivalent pre-release detection for all seven modeled fault classes with auditable evidence.
