# Streaming Rendition QA Pilot — Statement of Work

## Outcome

Produce a deterministic, hash-bound QA report over the buyer's supplied streaming rendition metadata so operations can see exactly which assets are internally consistent and which are held for remediation before the buyer's own release process continues.

## Diagnostic — $2,500 fixed

Buyer supplies a representative metadata export for 20–500 assets in, or mappable to, the release-gate packet contract. Seller provides normalization guidance, runs the deterministic QA gate, returns the hash-bound findings report, and conducts a remediation handoff focused on reason-coded failures.

Acceptance: the delivered report binds to a gate projection SHA-256, reports every supplied asset exactly once, separates `RELEASE_READY` from `HOLD`, and names the stable first hold reason for each failed asset.

## Integration — $7,500 fixed

Includes the Diagnostic scope plus integration of the QA receipt step into one existing buyer handoff path (for example, an internal export/job boundary), with a deterministic acceptance fixture and operator runbook for that integration.

Acceptance: the buyer can replay the agreed fixture through the integrated boundary and reproduce the agreed canonical report bytes and SHA-256.

## Payment / start condition

Kickoff is paid through a seller-approved invoice or payment link. The actual payment route is supplied by the commercial owner; this SOW does not fabricate one. Work starts after payment confirmation and receipt of the agreed metadata sample.

## Buyer responsibilities

The buyer owns source-of-truth metadata, rights decisions, content decisions, credential handling, DRM secrets, transcoding, storage/CDN mutation, scheduling, and publishing. The buyer must not include media payloads or DRM secrets in the pilot intake.

## Exclusions

No content editing; no rights determination; no DRM-secret retrieval; no transcoding; no media upload; no CDN mutation; no publication; no autonomous customer/provider mutation; no claim that metadata consistency proves end-user playback quality.

## Expansion path

If the pilot exposes recurring failure classes, the next paid scope can add buyer-specific normalization adapters, CI/CD gating, dashboard/export integration, or a larger evidence window. Expansion is separately priced rather than silently added to the pilot.
