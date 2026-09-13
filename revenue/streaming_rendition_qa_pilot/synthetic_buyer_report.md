# Synthetic Streaming Rendition QA report

**Synthetic proof only — no customer data, media bytes, DRM secrets, provider access, or release authority.**

Source carrier: Commons PR #13885, merged as `fed79e71c0c94c92568e5b555f50d2ad34ad0658`.

Canonical fixture: **168** synthetic asset packets → **140 RELEASE_READY / 28 HOLD**. The 28 HOLD packets are evenly distributed: exactly four per modeled fault class.

| Fault class | HOLD count | Synthetic asset IDs |
| --- | ---: | --- |
| `MISSING_RENDITION` | 4 | `asset-140`–`asset-143` |
| `CODEC_PROFILE_MISMATCH` | 4 | `asset-144`–`asset-147` |
| `SEGMENT_DISCONTINUITY` | 4 | `asset-148`–`asset-151` |
| `CAPTION_AUDIO_ALIGNMENT_GAP` | 4 | `asset-152`–`asset-155` |
| `DRM_REFERENCE_MISMATCH` | 4 | `asset-156`–`asset-159` |
| `CHECKSUM_ORPHAN_ARTIFACT` | 4 | `asset-160`–`asset-163` |
| `PUBLICATION_WINDOW_CONFLICT` | 4 | `asset-164`–`asset-167` |

Clean control: `asset-000` is expected to emit `RELEASE_READY` / reason `NONE`.

Fixture SHA-256: `27d34cc0574f3210e3e42c575f3615be9bd6d056f6f51576271bc7b6ecc79441`  
Projection SHA-256: `e510ed89458a54d32a6cda0da425d92612ed40783fb311c2db86d3ad33f889c2`

This report demonstrates the diagnostic shape only. It does not claim a buyer has accepted the offer, supplied data, paid, or realized savings.
