# Streaming Rendition QA Pilot

A bounded commercialization/diagnostic pack around the already-landed `streaming_rendition_release_gate` metadata engine. It does **not** replace that detector and does not expand its media authority.

The fixed diagnostic reference is **$2,500 for one buyer-owned sanitized metadata export of <=250 assets**. The **$7,500 integration reference is `OPTIONAL_AFTER_PAID_DIAGNOSTIC`** and is not an accepted contract or automatic next step.

The supported commercial proof promise is intentionally limited to the seven failure classes in the upstream canonical 168-asset acceptance fixture: missing rendition, codec/profile mismatch, segment discontinuity, caption/audio alignment gap, DRM-reference mismatch, checksum/orphan artifact, and publication-window conflict.

Production CLI owns current UTC:

```bash
python streaming_rendition_qa_pilot_standalone.py evaluate bundle.json --out-dir out
python streaming_rendition_qa_pilot_standalone.py verify bundle.json out/report.json
```

Prospect research is evidence-only and capped at ten rows. It may bind public HTTPS evidence and controlled streaming-operation tags, but never sends outreach, infers email addresses, scores intent, or grants contact authority.

Authority ceiling: no prospect contact, provider/account access, media-byte handling, DRM-secret retrieval, rights determination, transcoding, CDN mutation, publication, deployment, contract/signature, payment action, buyer-acceptance claim, cash assertion, or revenue recognition.
