# Streaming Rendition QA paid-pilot kit

Operation: `STREAMING-RENDITION-QA-PILOT-KIT-ZLCV7Q3-20260913`  
Owner/finalizer: `Z-LorentzCinder-914020-V7Q3` (`ZLC-V7Q3`) / GPT-5.6 Sol  
Commercialization issue: Commons #13923  
Technical source: Commons PR #13885 → merge `fed79e71c0c94c92568e5b555f50d2ad34ad0658`

This directory converts the already-landed, deterministic streaming rendition release gate into a bounded paid-pilot packet. It does **not** add streaming infrastructure. It packages proven synthetic QA evidence, fixed pilot-test pricing, a strict public-evidence prospect queue, and fail-closed checks that prevent source-proof drift or accidental authority inflation.

## What is sellable now

- **$2,500 metadata-only diagnostic:** one sanitized export, no more than 250 assets.
- **$7,500 integration sprint:** only after a paid diagnostic proves value and one bounded metadata adapter surface is agreed.

See `offer.md` for acceptance and stop rules. Prices are intentional pilot-test prices, not claimed market rates.

## Proof basis

The packet refuses to compile unless the landed source still matches:

- 168 canonical synthetic asset packets;
- 140 `RELEASE_READY` / 28 `HOLD`;
- seven fault classes, exactly four HOLDs each;
- fixture SHA-256 `27d34cc0574f3210e3e42c575f3615be9bd6d056f6f51576271bc7b6ecc79441`;
- projection SHA-256 `e510ed89458a54d32a6cda0da425d92612ed40783fb311c2db86d3ad33f889c2`.

`synthetic_buyer_report.md` is not hand-wavy copy: `build_pilot_packet.py` regenerates its facts from the source fixture and validator and rejects drift.

## Prospect queue

`prospects.json` contains exactly ten organizations with public first-party evidence of live/VOD, HLS/DASH, adaptive-bitrate, multi-CDN, or closely related streaming operations. The validator permits no email, phone, contact-name, credentials, or non-HTTPS evidence. Each row includes a falsifier so sales can disqualify rather than force-fit.

The queue is **research only**. It is not send authority and does not claim any organization is a customer, buyer, or active opportunity.

## Run

```bash
python3 test_streaming_rendition_qa_pilot.py
python3 -O test_streaming_rendition_qa_pilot.py
python3 revenue/streaming_rendition_qa_pilot/build_pilot_packet.py --check
python3 revenue/streaming_rendition_qa_pilot/build_pilot_packet.py --output /tmp/streaming-rendition-qa-pilot.json
```

All runtime code uses the Python standard library.

## Commercial stop rule

Stop this offer for a prospect if a sanitized manifest/export is impractical to provide or the buyer already has auditable checks covering all seven modeled fault classes. Do not turn a $2,500 diagnostic into free custom adapter work.

## Authority ceiling

This kit has no media ingestion, DRM-secret access, transcoding, CDN/provider mutation, publication, rights determination, release decision, private contact enrichment, contract/signature, checkout, or payment authority. `RELEASE_READY` remains a metadata-consistency result only.
