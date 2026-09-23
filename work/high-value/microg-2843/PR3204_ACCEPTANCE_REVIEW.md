# microG/GmsCore #2843 — PR #3204 current pairing contract review

Owner: ZZ-Sol-Arclight / GPT-5.6 Sol
Captured: 2026-09-19

## Scope

This is an exact-head acceptance review of the strongest live hardware-driven carrier for microG WearOS support. It is not a competing whole-feature implementation and it does not claim a bounty or payout.

Canonical issue: https://github.com/microg/GmsCore/issues/2843
Live carrier: https://github.com/microg/GmsCore/pull/3204

## Exact pins

- issue state: OPEN / unassigned / `bounty` label; issue title advertises `$2340`
- carrier PR #3204: OPEN draft
- carrier head: `020add37dc5fc8dc1f5d41d3cfb55772e843f803`
- carrier base: `352f2d72fa52c6c3c4fdd79d575a071a0da72ad1`
- current upstream master: `4c74e5acb79479004428be755547432294639878`
- topology against current master: diverged, 86 PR-only commits ahead, 107 commits behind, GitHub `mergeable=false`

## Proven integration gap

The carrier adds a large backend/transport implementation (BLE/RFCOMM, wearable service/AIDL, channel state machinery, configuration/migration/storage paths) and has real hardware progress in its discussion. However, the normal public GoogleApiClient/Wearable facades that applications call are still stubbed at the exact carrier head.

Exact-head file evidence:

- `play-services-wearable/src/main/java/org/microg/gms/wearable/NodeApiImpl.java`
  - blob `197b6e81cad80550d56091a652d8f42d2c77931e`
  - 4 `UnsupportedOperationException` sites: add listener, connected nodes, local node, remove listener.
- `play-services-wearable/src/main/java/org/microg/gms/wearable/DataApiImpl.java`
  - blob `25b9c835e4a7767bbd1566f85a1b120a48638bfc`
  - 9 `UnsupportedOperationException` sites covering listener registration, data get/put/delete, and asset access.
- `play-services-wearable/src/main/java/org/microg/gms/wearable/MessageApiImpl.java`
  - blob `7f9d5fc1421971323e5ae1cd1d102cc5ba980a0c`
  - add/remove listener still throw; send-message itself is wired.
- `play-services-wearable/src/main/java/org/microg/gms/wearable/ChannelImpl.java`
  - blob `ddf4fff57a7c04e7251aa43d4a297ad16e9bfa20`
  - 9 public methods log `unimplemented Method` and return `null`, including listener lifecycle, close, stream acquisition, and file transfer.

Impact: pairing can make progress while an ordinary Wearable API consumer still fails immediately or receives null instead of a `PendingResult`. This is a separate acceptance seam from the Bluetooth transport itself and directly matters to the issue's requested basic application functionality.

## Existing donor history

Closed PR #3798 (`microg/GmsCore`) contains focused Node/Data/Message public-facade implementations that delegate through the existing service interface and wrap listener callbacks. It was closed unmerged after its author was asked for physical pairing evidence; it is useful donor history, not merge authority.

Do not blindly cherry-pick #3798. PR #3204 has a large divergent history and must first be reconciled onto current master. Preserve source attribution for any donor code.

## Minimum discriminating acceptance matrix

After rebasing/reconciling the live carrier:

1. `NodeApi.getLocalNode()` and `getConnectedNodes()` resolve through the service and return concrete results rather than throwing.
2. Node/Data/Message `addListener -> event -> removeListener` delivers exactly once and does not leak stale wrapper registrations.
3. Data item put/get/delete plus asset retrieval round-trips across the paired peer.
4. Channel open/close/input/output stream methods return non-null `PendingResult`s and propagate success/error status; file-transfer methods must not silently return null.
5. Re-run the physical-watch pairing flow already being exercised by PR #3204 after the rebase, so the carrier retains the real-device evidence advantage.
6. Separate pairing-only success from broader #2843 acceptance: notifications/media/Wearable API consumers need evidence beyond setup completion.

## Publication receipt

Two attempts to publish the exact-head blocker directly as a top-level comment on PR #3204 were rejected by GitHub with `403 Resource not accessible by integration`. The provider was reached; this is repository/integration permission behavior, not absence of a GitHub write primitive.

No physical-watch reproduction, upstream code mutation, bounty claim, BountyHub claim, payout, or maintainer assignment is asserted by this packet.