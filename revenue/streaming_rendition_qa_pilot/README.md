# Streaming Rendition QA paid pilot

`STREAMING-RENDITION-QA-PILOT-ZFBC7M4-20260913` commercializes the already-landed metadata-only streaming rendition release gate without widening its authority.

The offer is deliberately bounded:

- **$2,500 fixed diagnostic** for one sanitized metadata export containing at most **250 asset packets**.
- **$7,500 fixed integration sprint** only after a completed paid diagnostic proves value and a concrete adapter boundary is known.
- The diagnostic emits deterministic `RELEASE_READY` / `HOLD` rows, stable reason codes, a concise owner-review report, and a content-addressed proof receipt.
- No custom adapter is included in the diagnostic price. No free speculative adapter work is promised.

These are test prices for this offer, not a claim about market rates.

## Proof, not marketing assertions

The packet is built from Commons PR #13885 / merge `fed79e71c0c94c92568e5b555f50d2ad34ad0658`. `build_proof_receipt()` reruns that landed source fixture through the landed gate and refuses to produce a commercial packet unless all of the following remain exact:

- 168 synthetic packets total;
- 140 metadata packets `RELEASE_READY` and 28 `HOLD`;
- exactly four holds in each of seven fault classes;
- canonical fixture SHA-256 `27d34cc0574f3210e3e42c575f3615be9bd6d056f6f51576271bc7b6ecc79441`;
- canonical result projection SHA-256 `e510ed89458a54d32a6cda0da425d92612ed40783fb311c2db86d3ad33f889c2`.

A change in gate behavior, fixture bytes, result projection, fault counts, or fault identities therefore fails the pilot proof closed instead of silently leaving stale sales copy behind.

## Buyer-facing bundle

Generate a fresh deterministic bundle into a new directory:

```bash
python3 -m revenue.streaming_rendition_qa_pilot.pilot /tmp/streaming-qa-pilot
```

The target must not already exist. The bundle contains:

- `synthetic-diagnostic.md` — one-page synthetic defect report;
- `scope-and-price.md` — pilot inputs, deliverables, acceptance boundary, and expansion option;
- `proof-receipt.json` — source-recomputed proof and commercial terms;
- `bundle-manifest.json` — SHA-256 binding for the three buyer-facing files plus the all-false external-authority map.

`sample/` contains a checked-in snapshot that tests require to match the live renderer byte-for-byte.

## Authority ceiling

This product is metadata-only pre-release QA. It does **not** ingest media bytes, retrieve DRM secrets, determine rights, edit media, transcode, publish, mutate a CDN/provider, authenticate payment, access production credentials, prove buyer acceptance, or recognize revenue. `RELEASE_READY` still means only that the supplied metadata contract is internally consistent; media operations retain release authority.
