# W03 CAST580-CHANNEL — CastV2 protocol layer for microg/GmsCore#580

Support lane for W01 (sole submitter). No PR, claim or upstream comment from this lane.
Status: IN PROGRESS (2026-10-01)

## Listing state (from the coordinator's inventory; not re-audited here)

| Listing | Advertised | Funded | Promised | Issue | PR (ours) | Claim | Merge | Payment |
|---|---|---|---|---|---|---|---|---|
| microg/GmsCore#580 listing A (emeitner) | $250 | $0 | $250 | OPEN | none (W01 submits) | none | none | none |
| microg/GmsCore#580 listing B (olofmogren) | $150 | $50 | $100 | OPEN | none (W01 submits) | none | none | none |

Competing open upstream PRs on #580: #3351, #3502, #3668, #3767 (none merged).

## Boundary assumed (W01 lane file not published when this lane started)

W03 owns, in `play-services-cast/core` and the client AIDL in `play-services-cast`:
- CastV2 channel: TLS to receiver port 8009, length-prefixed CastMessage framing, deviceauth, connection, heartbeat.
- Receiver namespace: GET_STATUS / LAUNCH / STOP / SET_VOLUME, session and transport IDs.
- `ICastDeviceController` / `ICastDeviceControllerListener` AIDL and `CastDeviceControllerImpl` / `CastDeviceControllerService`.
- Custom-namespace and media-namespace passthrough to the client binder.

Not owned: `CastMediaRouteProvider` (discovery, W02), `play-services-cast-framework` (W04).
`CastMediaRouteController` belongs to W04/W01; the only edit this lane makes there is removing the
dead import/field of the dropped library (separate commit, can be dropped if W04 replaces the file).
