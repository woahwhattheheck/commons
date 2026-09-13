# Sales handoff — Streaming Rendition QA Pilot

## Who to target

Prioritize teams that operate OTT/FAST/live/VOD rendition pipelines and visibly own release QA, media supply chain, streaming operations, or video platform reliability. Strong triggers include a recent platform migration, multi-CDN expansion, caption/audio compliance work, codec/profile expansion, or incident language around missing/incorrect renditions.

Do not target a company merely because it streams video. Require evidence of an operating workflow and a plausible owner for media delivery or release QA.

## Discovery questions

1. Where are rendition mismatches discovered today: packaging, pre-publication QA, CDN handoff, or after playback complaints?
2. Can the team export the expected-versus-produced rendition metadata for 20–500 assets without media payloads or DRM secrets?
3. Which failure classes cost the most operator time: missing rendition, codec/profile drift, segment continuity, caption/audio alignment, DRM-reference mismatch, checksum/artifact issues, publication-window conflict, or CDN-region drift?
4. What existing handoff would consume a reason-coded JSON report if the Diagnostic proves useful?
5. Who can approve a $2,500 fixed diagnostic, and what procurement step precedes paid kickoff?

## Positioning

Lead with the bounded operational outcome: deterministic metadata reconciliation before the buyer's own release process. Show the existing 168-packet synthetic acceptance evidence and the hash-bound report path. Never claim playback testing, rights verification, or publishing authority.

## Commercial close

The default close is the **$2,500 Diagnostic**. If the buyer already wants the deterministic gate inserted into an existing workflow, offer the **$7,500 Integration**. Make payment intent unambiguous: kickoff is paid through the seller-approved invoice/payment route. Do not send unpaid custom integration work as a substitute for closing the pilot.

## Proof to attach

- merged release-gate implementation: Commons PR #13885;
- 168 synthetic packets: 140 ready / 28 held;
- four holds in each of seven canonical failure classes;
- deterministic fixture and projection hashes;
- this pilot wrapper's deterministic 12-packet demo receipt and test output once merged.
