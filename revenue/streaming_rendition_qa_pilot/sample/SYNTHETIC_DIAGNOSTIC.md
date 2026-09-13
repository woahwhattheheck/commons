# Streaming Rendition QA — synthetic diagnostic

**Sample only. No customer media, production credentials, DRM secrets, or buyer data were used.**

- Assets evaluated: **168**
- Metadata packets release-ready: **140**
- Held for review: **28**
- Canonical fixture SHA-256: `27d34cc0574f3210e3e42c575f3615be9bd6d056f6f51576271bc7b6ecc79441`
- Canonical result projection SHA-256: `e510ed89458a54d32a6cda0da425d92612ed40783fb311c2db86d3ad33f889c2`

## Hold inventory

| Stable reason | Count | Synthetic examples |
| --- | ---: | --- |
| `MISSING_RENDITION` | 4 | asset-140, asset-141, asset-142, asset-143 |
| `CODEC_PROFILE_MISMATCH` | 4 | asset-144, asset-145, asset-146, asset-147 |
| `SEGMENT_DISCONTINUITY` | 4 | asset-148, asset-149, asset-150, asset-151 |
| `CAPTION_AUDIO_ALIGNMENT_GAP` | 4 | asset-152, asset-153, asset-154, asset-155 |
| `DRM_REFERENCE_MISMATCH` | 4 | asset-156, asset-157, asset-158, asset-159 |
| `CHECKSUM_ORPHAN_ARTIFACT` | 4 | asset-160, asset-161, asset-162, asset-163 |
| `PUBLICATION_WINDOW_CONFLICT` | 4 | asset-164, asset-165, asset-166, asset-167 |

## What this demonstrates

The landed gate deterministically checks rendition presence, codec/profile declarations, segment continuity, caption/audio alignment, DRM **reference IDs**, artifact checksum/orphan consistency, publication-window consistency, and CDN-region metadata. `RELEASE_READY` means only that supplied metadata is internally consistent; media operations retain release authority.

## Paid pilot

The bounded diagnostic is **$2,500 fixed** for one sanitized metadata export containing at most 250 asset packets. A separate **$7,500 integration sprint** is offered only after the paid diagnostic proves value and the adapter scope is known.

Not included: media bytes, DRM secrets, rights decisions, transcoding, CDN mutation, publishing, production credentials, payment authentication, or claims of buyer acceptance/revenue.
