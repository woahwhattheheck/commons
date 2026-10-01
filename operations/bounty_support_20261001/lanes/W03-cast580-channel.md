# W03 — CAST580-CHANNEL: CastV2 protocol layer for microg/GmsCore#580

Support lane for W01, the sole submitter. This lane opens no PR, files no BountyHub claim and posts no upstream comment.
State: **DELIVERED TO W01.** Three patches against base `32bc8954` (2026-10-01). Each builds. A host-side run against a software receiver passes.

## Listing state

Listing IDs come from W01's lane file. This lane did not re-audit them.

| Listing | Advertised / funded / promised | Issue | PR | Claim | Merge | Payment |
|---|---|---|---|---|---|---|
| `ef91cb1e-dd69-4a33-bd90-21c9679c9247` (Chromecast + Tizen) | $150 / $50 / $100 | #580 OPEN | none (W01 submits) | none | none | none |
| `27c3cfe0-da9e-4192-848a-b676402de81c` (Roku) | $250 / $0 / $250 | #580 OPEN | none | none | none | none |

Roku and Tizen are not Cast receivers; see W01's lane file. This channel work serves the Chromecast part of `ef91cb1e`.

## Deliverable

- Branch: local `cast-channel` in `~/work/GmsCore` (this session's VM), base `microg/GmsCore@32bc8954`.
- Patches (`git am`, in order). Applying them to a clean `32bc8954` reproduces the branch tree exactly (`dc6e7d45`):
  - `operations/bounty_support_20261001/patches/W03/0001-Cast-Add-CastV2-channel-to-talk-to-receivers-directl.patch`
  - `operations/bounty_support_20261001/patches/W03/0002-Cast-Implement-the-device-controller-on-the-CastV2-c.patch`
  - `operations/bounty_support_20261001/patches/W03/0003-Cast-Drop-chromecast-java-api-v2.patch`
- Author on the patches: `woahwhattheheck <woahwhattheheck@users.noreply.github.com>`. This is a placeholder. W01 sets the final submission identity. The patches carry no trailers, footers, tool names or lane names.

| Patch | Files | Owner per W01's boundary |
|---|---|---|
| 0001 | `play-services-cast/core/src/main/proto/cast_channel.proto` (new), `.../kotlin/org/microg/gms/cast/channel/CastChannel.kt` (new), `.../channel/CastDeviceSession.kt` (new), `play-services-cast/core/build.gradle` (adds the Wire plugin and `wire-runtime`) | W03, plus a build.gradle change **filed to W01** |
| 0002 | `ICastDeviceController.aidl`, `ICastDeviceControllerListener.aidl`, `ICastService.aidl`, `CastDeviceControllerService.java`, `CastDeviceControllerImpl.java` (deleted), `.../kotlin/org/microg/gms/cast/CastDeviceControllerImpl.kt` (new), `CastServiceImpl.kt` (new), `CastChannelRegistry.kt` (new) | W03 |
| 0003 | `play-services-cast/core/build.gradle` (drops the library), `CastMediaRouteController.java` (removes 4 dead imports, 1 unused field and its assignment), `play-services-core/.../ui/AboutFragment.java` (removes the library credit line) | **W01 / W02 files.** If W02's patch rewrites `CastMediaRouteController.java`, drop that hunk; the only requirement is that no `su.litvak` import remains. |

Interface for W02 (W01 interface 3): `CastChannelRegistry.get(deviceId)` returns the `CastDeviceSession` of a connected device, or null. Call `setVolume(level: Double)` / `setMute(muted)` on it. It is a Kotlin `object` with `@JvmStatic` methods, so Java calls it exactly as `CastChannelRegistry.get(id)`. The file is `.kt`, not the `.java` W01's plan named; the API is the same.

## Decision: replace `chromecast-java-api-v2` with an in-tree channel

Evidence:
- **Maintenance.** Upstream `vitalidze/chromecast-java-api-v2` last committed on 2020-11-20. The raw-request support microG needs (vitalidze PR #99, `armills` fork) was never merged. microG pins that fork's `0.10.4-raw-request-1` jar, which pulls in Jackson 1.9 (codehaus), protobuf-java 2.6, jmdns and slf4j.
- **Every client message cost a blocking `GET_STATUS` round trip.** The fork's `ChromeCast.sendRawRequest(ns, msg, id)` calls `getStatus()` (up to a 30 s wait) and then sends to "the running app" rather than the session the client joined.
- **Request-id collisions.** The library matches *any* incoming JSON carrying `requestId` against its own counter, which starts at 1, across all namespaces. App replies with small request ids can be swallowed or misparsed. microG also fired `onSendMessageSuccess` with the *response payload* on every incoming message with a requestId. The listener contract is (namespace, requestId) after the write.
- **Missing operations.** The library has no join by session; microG's `joinApplication` relaunched the app and killed the running session. It also lacks leave, mute, requestStatus and binary send, and has no per-transport virtual-connection control.
- **Threading.** All calls block a binder thread on network I/O with 30 s timeouts, and oneway calls from one client serialize behind them.

The replacement is 950 lines of Kotlin across 5 files, comments included, plus a 55-line proto schema. It uses Wire, which is already used across microG, and adds no new third-party dependency.

## Evidence from the shipped Cast SDK (how the codes were chosen)

Source: Google Maven `com.google.android.gms:play-services-cast:22.3.1`, whose `classes.jar` I disassembled with `javap -c`, cross-checked against `9.0.0`. Codes below are raw binder codes; the AIDL `= N` value is the code minus 1.
- **ICastDeviceController (proxy `cast.internal.zzah`):** 1 disconnect, 4 leaveApplication, 5 stopApplication(String), 6 requestStatus, 7 setVolume(double,double,bool), 8 setMute(bool,double,bool), 9 sendMessage, 11 registerNamespace, 12 unregisterNamespace, 13 launchApplication(String, LaunchOptions), 14 joinApplication(String, String, JoinOptions-compatible `zzbn`), 17 connect(), 18 addListener(listener), 19 removeListener(). In 9.0.0, 10 is sendBinaryMessage(String, byte[], long) and 2/3 are the deprecated launch/join. All calls are oneway, and each appends an `ApiMetadata` parcelable that the stub ignores.
- **ICastDeviceControllerListener (stub `cast.internal.zzai`, dispatch read by offset):** 1 onDisconnected, 2 onApplicationConnectionSuccess, 3 onApplicationConnectionFailure, 5 text, 6 binary, 7 and 8 both complete the pending leave/stop result, 9 onApplicationDisconnected, 10 onSendMessageFailure(ns, id, status), 11 onSendMessageSuccess(ns, id), 12 application status, 13 device status, **14 onConnectedWithResult(status)** (0 → client state CONNECTED), 15 onConnectionSuspended.
- **The connectionless client is what current apps use** (`cast.zzbm` via `cast.internal.zzy`). It binds with no `listener` in the extras, calls 18 then 17, and stays not-connected until it gets listener code 14. Its register call `setFeatures(cxless_client_minimal)`, so the service must advertise that feature in `ConnectionInfo` or the call fails before reaching the device. Master implements neither.
- **Service id 161 (`CAST_API`, client `cast.internal.zzo`)** binds the *same* action `BIND_CAST_DEVICE_CONTROLLER_SERVICE` but expects `com.google.android.gms.cast.internal.ICastService`. Codes: 2 broadcastPrecacheMessage, 5 getFeatureFlags (feature `module_flag_control`), 6 getCastStatusCodeDictionary (`analytics_proto_enum_translation`), 7 integer maps (`integer_to_integer_map`). On master nothing serves 161, so the bind fails.

I compared microG's generated `Stub.TRANSACTION_*` constants after the change with the codes above, and every code matches.

## What the patches implement

- **Channel:** TLS to the device's service port (default 8009); 4-byte big-endian length-prefixed `CastMessage`; deviceauth challenge, failing on `AuthError`; CONNECT/CLOSE virtual connections per transport; heartbeat PING every 5 s, PONG to receiver PINGs, close after 20 s silent; 64 KiB payload limit (`MESSAGE_TOO_LARGE`).
- **Receiver namespace:** GET_STATUS on connect and on request; LAUNCH joins the running instance unless `relaunchIfRunning`, and passes `language`; LAUNCH_ERROR maps to 2004/2002/2003/15/2100; STOP; SET_VOLUME level/muted; join by app id and/or session id; leave closes only the virtual connection. Internal request ids are matched only for replies from `receiver-0` on the receiver namespace.
- **Routing:** messages from the attached app's transport, addressed to us or broadcast (`*`), go to the client for namespaces it registered. Text and binary are both delivered, including the media namespace. `sendMessage` / `sendBinaryMessage` go to the app's transportId. `tp.*` and receiver namespaces are refused with 2001. With no app attached the result is 2005.
- **Service:** the legacy client (listener in extras) gets `onPostInitComplete` after the device connects; on failure it gets 7 or 2000. The cxless client follows 18 → 17 → listener 14. 161 is answered with `CastServiceImpl`, which returns empty bundles and SUCCESS. Both answers carry `ConnectionInfo` features.
- **Status:** RECEIVER_STATUS maps to `CastDeviceStatus` (volume, mute, active input, standby, app metadata) and to `ApplicationStatus` when the status text changes. App gone → `onApplicationDisconnected` (2005, or 0 after our own STOP). Socket loss → `onDisconnected(7)`.
- **Threading:** one session thread per controller; binder calls return at once and keep their order.

## Runs (this VM)

- Builds (JDK 21, SDK 35, Gradle wrapper 8.13), all exit 0:
  - `:play-services-cast-core:compileDebugJavaWithJavac` at 0001, at 0002 and at 0003 (separate worktrees, so the series bisects).
  - Full app `:play-services-core:assembleVtmDefaultDebug` at 0003 → `com.google.android.gms-252432035.apk`. dexdump of the APK: 0 `su.litvak` classes, 0 `org.codehaus.jackson` classes; `CastChannel`, `CastDeviceSession`, `CastDeviceControllerImpl`, `CastServiceImpl`, `CastChannelRegistry` and the generated `proto.CastMessage` are present.
  - Earlier attempts failed only on HTTP 429 from repo.maven.apache.org while resolving dependencies. They were retried unchanged; no code change between attempts.
- **Host-side protocol run.** I ran the module's compiled `CastChannel` / `CastDeviceSession` classes from `build/tmp/kotlin-classes/debug`, with wire-runtime, okio, kotlin-stdlib and org.json, against a software CastV2 receiver: Python, TLS, the real framing, deviceauth, connection, heartbeat, receiver namespace, and per-app transports with an echo namespace and the media namespace. Exit 0. Every step passed:
  - closed port → connectionFailed 7
  - connect → initial status (level 1.0, active input, not standby)
  - launch `E1C0DE01` → appConnected (launched=true)
  - custom namespace text round trip + sendOk(ns, id) + app status text change
  - binary round trip
  - media LOAD → MEDIA_STATUS reply + broadcast delivered
  - unregistered namespace not delivered
  - setVolume 0.4 / setMute → device status
  - launch without relaunch → joins the same session (launched=false)
  - unknown app id → 2004
  - `tp.connection` send → 2001; 70 000-char payload → 2006
  - leave → result 0, then send → 2005
  - join by session id → attached (launched=false)
  - relaunch → old session reported gone (2005) and a new session attached
  - 25 s idle with heartbeat (5 PING/PONG) → channel still alive, echo works
  - stop → appDisconnected 0 + stopResult 0 (ordering bug found and fixed here: the receiver's transport CLOSE arrives before the STOP reply)
  - local disconnect → CLOSE to the app transport and receiver-0, no disconnected callback
- **Second run:** the receiver process is killed mid-session → `disconnected 7`, exit 0.

The receiver and driver are scratch tools and are not committed (RULES 17).

## Not covered / known limits

- **No real Chromecast run.** None is reachable from the cloud VM. A device run on Bryce's LAN is W01's existing owner blocker.
- The deviceauth response signature is not verified against the Cast root CA. Master behaves the same way.
- Deprecated codes 2/3 (pre-2016 SDK launch/join) are not implemented.
- On network loss the session reports disconnected and does not auto-reconnect; `onConnectionSuspended` is declared but unused.
- `LaunchOptions.credentialsData` is not forwarded. `ApplicationMetadata.senderAppIdentifier` is left null; master set it to microG's own package name, which was wrong.
- The 22.3.1 `CastDeviceStatus` parcel has fields 7 (Parcelable) and 8 (double, step interval) that microG's class lacks. That class is W01-owned and SafeParcel tolerates the missing fields.

## Relation to open community PRs

- **#3570 (peterhel).** Uses the same connectionless codes (connect 17, setListener 18, unregister 19, onConnectedWithResult listener 14), matching the SDK disassembly above. It also accepts `CAST_API` (161), but answers it with the device controller binder rather than an `ICastService`, and advertises every requested feature, including ones it does not implement. It keeps the library. This series covers its controller and service changes; its framework-side commit (start session on route select) is W04's area. No code was taken from it.
- **#3802.** Moves `connect()` to AIDL `= 17` (binder code 18, the SDK's addListener) and renumbers stop/volume, which does not match the SDK proxies. Not used.
- **#3781.** Uses the same connectionless codes as #3570; it also touches `gradle.properties`, the manifest and `CastDevice`. Not used.
- **#3351, #3377, #3470.** Built on the library; superseded by this channel for the device-controller files.

## Coordination (for the coordinator to relay; this lane cannot post to Slack)

- The orders thread has a new internal claim, **`BH-CAST-IMPLEMENT-580`**: "Cast v2 implementation across the assigned cast and cast-framework modules … establish discovery/transport and framework routing". It was dispatched after the "BH-CAST-ANALYSIS-580" note. Its scope overlaps W01 (sole submitter), W02 (discovery), this lane (transport/channel, already delivered above) and W04 (framework).
- Under the one-writer rule, the coordinator should point that worker at W01, so the transport is not implemented a second time and no second #580 PR goes out under woahwhattheheck.
- In the same thread, the analysis note "no competing implementation PRs exist" is wrong. The open upstream PRs are listed above and in W01's file.

## State and next action

- Fork `woahwhattheheck/GmsCore`: **does not exist** (`git ls-remote` at 2026-10-01 ~12:10Z asks for credentials, which is GitHub's response for a missing repo). This lane needs no fork.
- **Next (W01):** `git am` the three patches after W02's and before W04's; drop the 0003 `CastMediaRouteController` hunk if W02 replaced the file. Then build, run on a real Chromecast, and submit.
- No PR, claim or upstream comment was made by this lane.

