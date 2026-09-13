# Streaming Rendition QA Pilot — scope / price / acceptance

**Diagnostic:** $2,500 fixed · one sanitized metadata export · <= 250 asset packets.

## Buyer supplies

- One sanitized metadata export mapped to the documented packet schema.
- No media bytes, DRM keys/secrets, production credentials, viewer PII, or rights-confidential material.
- A human technical owner for questions about field meaning and export completeness.

## We deliver

- Deterministic per-asset `RELEASE_READY` / `HOLD` results with stable reason codes.
- Defect inventory across rendition, codec/profile, continuity, caption/audio alignment, DRM-reference, checksum/orphan, publication-window, and CDN-region metadata consistency.
- Content-addressed proof receipt and a concise owner-review diagnostic summary.
- One readout of findings and adapter-fit observations; no production mutation.

## Diagnostic acceptance

The diagnostic deliverable is complete when the supplied export has been processed under the agreed schema, the deterministic result/proof receipt is delivered, every held row carries a stable reason, and the owner-review summary reconciles to that receipt. Acceptance of this artifact does not mean a media asset is safe or authorized to publish.

## Expansion option

A $7,500 fixed integration sprint may be scoped **only after the paid diagnostic is complete** and a concrete adapter boundary is known. No custom adapter is included in the diagnostic price and no free speculative adapter work is promised.

## Authority ceiling

This pilot is metadata-only pre-release QA. It does not determine rights, access DRM secrets, edit media, transcode, publish, mutate a CDN/provider, authenticate payment, establish buyer acceptance, or recognize revenue.
