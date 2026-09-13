# Streaming Rendition QA Pilot

`streaming-rendition-qa-pilot-20260913`

A sellable wrapper around the merged deterministic metadata gate in `revenue/streaming_rendition_release_gate/`. It converts a buyer's rendition packet batch into a hash-bound QA receipt that can be attached to an operations handoff without pretending to publish, transcode, inspect DRM secrets, or decide rights.

## Offer

| Tier | Fixed price | Delivery |
| --- | ---: | --- |
| Diagnostic | **$2,500** | Intake normalization guidance, deterministic batch run, reason-coded findings, hash-bound report, and remediation handoff |
| Integration | **$7,500** | Everything in Diagnostic plus integration of the deterministic QA step into the buyer's existing rendition handoff workflow |

Commercial intent is explicit: kickoff is paid using a **seller-approved invoice or payment link**. This repository deliberately does not invent a payment URL or imply receipt of funds.

## Buyer fit

Best fit is a streaming/video operations team that already has rendition metadata but loses time to late discovery of missing renditions, codec/profile drift, segment discontinuity, caption/audio alignment gaps, DRM-reference mismatch, artifact/checksum errors, publication-window conflict, or CDN-region drift.

The pilot is strongest where a buyer can export the metadata contract for 20–500 representative assets. No media payloads or DRM secrets are required.

## Intake contract

```json
{
  "schema": "streaming-rendition-qa-pilot/v1",
  "pilot_id": "buyer-pilot-001",
  "customer_ref": "buyer-internal-ref",
  "tier": "DIAGNOSTIC",
  "packets": ["<streaming-rendition-release-gate/v1 packets>"]
}
```

The wrapper is fail-closed on unknown intake keys, malformed refs, unknown tiers, empty packet sets, and batches above 5,000 packets. Individual packet ambiguity is delegated to the already-merged release gate and becomes a reason-coded `HOLD`.

## Output contract

`compile_receipt()` returns:

- canonical buyer-facing report bytes;
- SHA-256 of those exact report bytes;
- gate projection SHA-256 binding the report to the deterministic lower-level findings;
- total / ready / hold counts;
- stable reason counts and findings;
- `PASS_TO_MEDIA_OPS` only when every supplied packet is `RELEASE_READY`, otherwise `REMEDIATE_METADATA`;
- fixed-price commercial metadata and an explicit paid-kickoff expectation.

`PASS_TO_MEDIA_OPS` is **not** permission to publish. Media operations retain rights, content, release, scheduling, DRM-secret, transcoding, CDN, and publishing authority.

## Deterministic demo

The demo selects 12 packets from the existing canonical 168-packet fixture: five clean packets plus one example from each of the seven required fault classes. Expected result:

- total: 12
- release ready: 5
- hold: 7
- one hold in each required fault class
- decision: `REMEDIATE_METADATA`

Run:

```bash
python3 -m revenue.streaming_rendition_qa_pilot.demo
python3 test_streaming_rendition_qa_pilot.py
python3 -O test_streaming_rendition_qa_pilot.py
```

For a buyer JSON intake:

```bash
python3 -m revenue.streaming_rendition_qa_pilot.validate_intake buyer-intake.json --output buyer-report.json
```

## Evidence / acceptance

A shippable pilot must demonstrate:

1. deterministic identical report bytes on identical input;
2. report hash recomputes from exact bytes;
3. the demo remains `5 RELEASE_READY / 7 HOLD` with one hold per canonical fault class;
4. clean canonical packets produce `PASS_TO_MEDIA_OPS` without claiming publication authority;
5. hostile wrapper fields fail closed;
6. source gate schema failures are surfaced as `HOLD`, not swallowed;
7. prices remain exactly $2,500 Diagnostic / $7,500 Integration unless the commercial owner intentionally revises both code and SOW.
