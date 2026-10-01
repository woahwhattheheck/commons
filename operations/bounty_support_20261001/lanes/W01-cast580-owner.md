# W01 — CAST580-OWNER (microg/GmsCore#580, Google Cast)

Owner: W01 (sole submission owner). Coordinator: session_011V9kL56ttiXoNxPUNn7SHK.
Base: `microg/GmsCore` master @ `32bc8954` (2026-10-01 clone).

## Listings — separate acceptance states

| Listing | Amount | Sponsor criterion | State |
|---|---|---|---|
| `27c3cfe0-da9e-4192-848a-b676402de81c` | $250 advertised, PROMISED | "Implement casting so that e OS 3.x+ can cast to a Roku device" | OPEN — not achievable as stated through Cast (see Roku below). Intake not done. |
| `ef91cb1e-dd69-4a33-bd90-21c9679c9247` | $150 total, $100 funded/PAID | "fully working ... YouTube (native or ReVanced), Crunchyroll, Netflix, etc. cast to my TV running Tizen and a Chromecast" | OPEN — Chromecast target is in scope of this work. Tizen TV is DIAL, not Cast (see below). Intake not done. |

Sponsor intake (RULES 29) is required on BountyHub for each listing before funded work is claimed.

### Roku (listing 27c3cfe0)
Roku devices are not Google Cast receivers. They expose DIAL (SSDP `urn:dial-multiscreen-org:service:dial:1`) and Roku ECP (port 8060). Cast sender apps (YouTube, Netflix, Crunchyroll) use the proprietary cast-framework, which drives CastV2 namespaces (`urn:x-cast:com.google.cast.media`, app-private namespaces) against a receiver app identified by a Cast app ID. A Roku cannot run Cast receiver apps, so GmsCore cannot make an arbitrary Cast sender play on a Roku. What is achievable:
- YouTube and Netflix already have their own DIAL paths in their apps (independent of Play services); whether they appear on e/OS with microG is an app-side behaviour to record on device, not something GmsCore implements.
- A GmsCore-side DIAL "launch app X on Roku" route is technically possible but would not carry the sender's Cast session; it is out of scope for an upstream microG PR unless the maintainers ask for it.
Recorded state: NOT ACHIEVABLE via Cast; listing stays open until the sponsor confirms what they accept.

### Tizen TV (listing ef91cb1e)
Samsung Tizen TVs are not Cast receivers either. YouTube/Netflix reach them via DIAL from the app itself. The Chromecast half of that listing is what this PR series delivers.

## Upstream state of #580 (as of 2026-10-01)

- #580 "What's the status on Google Cast implementation?" is OPEN, label "📺 Chromecast", opened 2018-07-17. mar-v-in has commented on it, but this session could not fetch the comment text (api.github.com returned 403 for issue comments).
- The predecessor, #79, was closed by **#555 "MVP Cast API"** (emlove / Adam Mills, merged 2019-05-27). That PR is the code on master today. #528 (emlove) was closed by its author in favour of #555.
- **BountyHub-driven PRs closed by the maintainer:**
  - **#3417** (TeapoyY, 2026-04-20, "for BountyHub bounty") was labelled "AI slop" and had compile errors. mar-v-in, 2026-04-26: "What did you expect from AI slop?"
  - **#3767** (2026-09-01) was labelled "AI slop" and closed 2026-09-09.
- **Open community PRs, none reviewed yet:**
  - #3351: lifecycle / joinApplication
  - #3354: thread safety
  - #3377: "Fix casting"
  - #3470 (draft): socket off the main thread
  - #3505: CastMediaRouteController
  - #3554: dynamite ModuleDescriptor
  - #3567: start session on route select
  - #3570 (peterhel): `Cast.API_CXLESS` device controller. Author reports Prime Video, Netflix and Disney+ playing end to end; CI green.
  - #3577: no-op ReconnectionService
  - #3668
  - #3781: connectionless API, linked from #580
  - #3802: transaction IDs for the connectionless API
- /e/ OS has backlog issue #6801 "Chromecast not working", open with no fix.

**Submission consequence.** Another from-scratch AI-generated cast PR would repeat #3417 and #3767. The submission plan is therefore:
1. Build on the open community PRs, with author credit (`Co-authored-by`), rather than re-implementing them.
2. Keep every change small, compiling and verified on a real device.
3. Open nothing upstream until it has been run against a real Chromecast.

The PR text says plainly how the code was produced. Opening the PR is Bryce's call (fork + identity) and is listed as a blocker below.

### Lane starting points from open PRs
- W02: #3505 (CastMediaRouteController), #3354 (thread safety), #3470 (socket off main thread, provider side)
- W03: #3570, #3781, #3802 (connectionless API + transaction IDs), #3351 (joinApplication / lifecycle), #3377
- W04: #3554 (ModuleDescriptor), #3567 (session on route select), #3577 (ReconnectionService)
Fetch with `git fetch https://github.com/microg/GmsCore pull/<N>/head:pr-<N>`. Note overlaps in the patch header.

## What master has today (32bc8954)

- `play-services-cast` (client lib + AIDL) and `play-services-cast/core` (service): mDNS discovery via `NsdManager` in `CastMediaRouteProvider`; CastV2 transport via `info.armills.chromecast-java-api-v2:api-v2-raw-request:0.10.4-raw-request-1` in `CastDeviceControllerImpl`. `launchApplication`, `stopApplication`, `sendMessage` work; `registerNamespace`/`unregisterNamespace` are no-ops, `joinApplication` relaunches, `CastMediaRouteController` (select/volume) is all stubs.
- `play-services-cast-framework/core`: `CastDynamiteModuleImpl`, `CastContextImpl`, `SessionManagerImpl`, `SessionImpl`, `CastSessionImpl`, `DiscoveryManagerImpl`, `MediaRouterCallbackImpl` — mostly stubs (listeners, startSession, endCurrentSession, onRouteSelected, media notification, reconnection, bitmap fetch all unimplemented).
- `play-services-core/.../chimera/container/DynamiteLoaderImpl.java` returns version 1 for `com.google.android.gms.cast.framework.dynamite` with the log line "Cast API wil not be functional!", and there is no `dynamite/descriptors/com/google/android/gms/cast/framework/dynamite/ModuleDescriptor`.

Net: apps using `CastContext` (YouTube, Netflix, Crunchyroll — all of them) load the module but never get routes, sessions or state callbacks, so the cast button never becomes usable.

## Call path real apps take (the contract between lanes)

```
app CastContext (proprietary, in app)
  └─ DynamiteModule "com.google.android.gms.cast.framework.dynamite"     [W04]
       └─ CastDynamiteModuleImpl → CastContextImpl / SessionManagerImpl / SessionImpl
            ├─ IMediaRouter / MediaRouterCallbackImpl → androidx MediaRouter in app process
            │     └─ MediaRouteProviderService in GmsCore → CastMediaRouteProvider [W02]
            └─ app CastSession → Cast.CastApi (proprietary client in app)
                  └─ binds BIND_CAST_DEVICE_CONTROLLER_SERVICE → ICastDeviceController [W03]
                        └─ CastV2 TLS socket :8009 to Chromecast
```

Binder transaction codes and listener codes in every AIDL above must match Play services, because the client side lives inside the apps and is not ours.

### Interfaces fixed now

1. **Route ↔ device (W02 → W04).** Route ID = `CastDevice.getDeviceId()`. Route extras carry the `CastDevice` via `CastDevice.putInBundle(bundle)` (key `com.google.android.gms.cast.EXTRA_CAST_DEVICE`). Route control filters: `CastMediaControlIntent.CATEGORY_CAST`, plus per-app `CastMediaControlIntent.categoryForCast(appId)` / `categoryForCast(appId, namespaces)` accepted on discovery requests (W02 parses the selector's categories). W04 reads the device back with `CastDevice.getFromBundle(route.getExtras())` in `SessionManagerImpl.onRouteSelected`.
2. **Device → channel (W02 → W03).** `CastDevice` fields W02 must fill from TXT records: `id`, `fn` (friendly name), `md` (model), `ca` (capabilities bitmask), `ve`, `rs`, `ic`, host `InetAddress`, port. W03 connects with `CastDevice.getAddress()`/`getServicePort()` only.
3. **Route volume (W02 → W03).** `CastMediaRouteController.onSetVolume/onUpdateVolume` call W03's `org.microg.gms.cast.CastChannelRegistry` (new, W03) `get(deviceId)?.setVolume(level)`; if no open channel, no-op. W03 publishes this one class; W02 calls only it.
4. **Session (W04 → W03).** W04 never opens sockets. Session start/end goes through the app's own `CastSession` → `ICastDeviceController`. W04's `CastSessionImpl` relays state (`onConnected`, `onConnectionSuspended`, `onConnectionFailed`, `disconnectFromDevice`) between the app and `SessionImpl`.

## Lane boundaries (exact files)

### W02 — discovery / MediaRouteProvider
Owns:
- `play-services-cast/core/src/main/java/org/microg/gms/cast/CastMediaRouteProvider.java`
- `play-services-cast/core/src/main/java/org/microg/gms/cast/CastMediaRouteController.java`
- `play-services-cast/core/src/main/java/com/google/android/gms/cast/media/CastMediaRouteProviderService.java`
Deliver: reliable `_googlecast._tcp` discovery (serialize `NsdManager.resolveService`, which only resolves one service at a time below API 34; re-resolve on IP change; remove routes on `onServiceLost`); TXT parsing per interface 2; `MediaRouteDescriptor` with volume handling, connection state, device icon/description; discovery request parsing per interface 1; `onSelect`/`onUnselect`/volume per interface 3.

### W03 — CastV2 channel / session / app launch
Owns:
- `play-services-cast/core/src/main/java/org/microg/gms/cast/CastDeviceControllerImpl.java`
- `play-services-cast/core/src/main/java/org/microg/gms/cast/CastDeviceControllerService.java`
- new `play-services-cast/core/src/main/java/org/microg/gms/cast/CastChannelRegistry.java` (and any new channel classes under `play-services-cast/core/src/main/{java,kotlin}/org/microg/gms/cast/channel/`)
- `play-services-cast/src/main/aidl/com/google/android/gms/cast/internal/ICastDeviceController.aidl`, `ICastDeviceControllerListener.aidl`, `ICastService.aidl`, `IBundleCallback.aidl`
- `play-services-cast/src/main/java/org/microg/gms/cast/{CastClientImpl,CastApiImpl,CastApiClientBuilder}.java`
Deliver: every `ICastDeviceController` transaction Play services exposes (launch with `LaunchOptions.relaunchIfRunning`, real join by sessionId, stop, sendMessage, register/unregister namespace with per-`transportId` virtual connections, setVolume, setMute, requestStatus), listener callbacks with Play-services codes, heartbeat, receiver status → `ApplicationStatus`/`CastDeviceStatus`, disconnect reasons. Decision on keeping `chromecast-java-api-v2` vs an in-tree channel is W03's; any gradle dependency change is filed to W01.

### W04 — cast-framework dynamite module + Roku/DIAL
Owns:
- everything in `play-services-cast-framework/core/src/main/java/com/google/android/gms/cast/framework/internal/`
- `play-services-cast-framework/src/main/aidl/**` and `play-services-cast-framework/src/main/java/**`
- new `play-services-core/src/main/java/com/google/android/gms/dynamite/descriptors/com/google/android/gms/cast/framework/dynamite/ModuleDescriptor.java`
- the `cast.framework.dynamite` branch in `play-services-core/src/main/java/com/google/android/gms/chimera/container/DynamiteLoaderImpl.java` (that branch only)
- Roku/DIAL feasibility: SSDP + DIAL REST probe as a standalone tool under `operations/bounty_support_20261001/w04/` in commons, not in the GmsCore tree. Output: per-device record of what launches.
Deliver: `SessionManagerImpl` listeners/startSession/endCurrentSession/onRouteSelected/onRouteUnselected, cast state transitions (`NO_DEVICES_AVAILABLE` → `NOT_CONNECTED` → `CONNECTING` → `CONNECTED`), `SessionImpl` notify* methods, `DiscoveryManagerImpl`, `MediaRouterCallbackImpl`, `CastContextImpl` (options, receiver app id, visibility), `newMediaNotificationServiceImpl`, `newReconnectionServiceImpl`, `newFetchBitmapTaskImpl`.

### W01 — integration (this lane)
Owns everything in the cast path not listed above:
- `play-services-cast/core/build.gradle`, `play-services-cast-framework/core/build.gradle`, `play-services-core/build.gradle`, `settings.gradle`
- `play-services-cast/core/src/main/AndroidManifest.xml`, `play-services-cast-framework/core/src/main/AndroidManifest.xml`, cast entries in `play-services-core/src/main/AndroidManifest.xml`
- public parcelables `play-services-cast/src/main/java/com/google/android/gms/cast/*.java` and their `.aidl` declarations (field changes requested by W02/W03 land here)
- building GmsCore, merging lane patches, the upstream PR(s) and review.

## Hand-off format

Fork of GmsCore does not exist yet. Until it does, each lane publishes `git format-patch` output against base `32bc8954` on its own commons branch at `operations/bounty_support_20261001/patches/W0N/*.patch`. W01 applies them in order W02 → W03 → W04, builds, and records the build result here. When the fork exists, lanes push `cast/W0N-*` branches to it instead.

## Owner blockers

- Fork `woahwhattheheck/GmsCore` does not exist; creating it and opening an upstream PR under Bryce's identity is his decision.
- BountyHub sponsor intake for both listings (RULES 29).
- No real Chromecast, Tizen TV or Roku reachable from the cloud VM; device verification needs Bryce's LAN (e/OS phone + Chromecast).

## Integration log

- 2026-10-01: base cloned, current-state survey above.
- 2026-10-01: VM toolchain: OpenJDK 21, Android cmdline-tools, platform 35 and build-tools 35.0.0 under `/home/user/android-sdk`. Baseline `:play-services-cast-core:compileReleaseJavaWithJavac :play-services-cast-framework-core:compileReleaseJavaWithJavac` on master exit 0. The VM has no `/dev/kvm`, so no emulator; every runtime check needs a real phone and Chromecast.
- 2026-10-01: **Binder ground truth** from Google's `com.google.android.gms:play-services-cast:22.3.1` client (`classes.jar`, read with `javap`; proxy `cast.internal.zzah`, stub `cast.internal.zzai`). AIDL `= N` gives transaction code N+1.
  - `ICastDeviceController` codes:

    | Code | Method |
    |---|---|
    | 1 | disconnect |
    | 4 | no-arg call, unidentified (possibly leaveApplication) |
    | 5 | stopApplication(String) |
    | 6 | no-arg call, unidentified (possibly requestStatus) |
    | 7 | setVolume(double, double, boolean) |
    | 8 | setMute(boolean, double, boolean) |
    | 9 | sendMessage(String, String, long) |
    | 11 | registerNamespace |
    | 12 | unregisterNamespace |
    | 13 | launchApplication(String, LaunchOptions) |
    | 14 | joinApplication(String, String, JoinOptions) |
    | 17 | connect() (connectionless) |
    | 18 | setListener(listener) |
    | 19 | unregisterListener() |

    Every 22.3.1 call also appends a trailing `ApiMetadata` parcelable.
  - `ICastDeviceControllerListener` codes 1–15. Codes 1–13 match master's AIDL. Code 14 is an int callback, which #3570 maps to `onConnectedWithResult` (`= 13`). Code 15 is an int callback that no PR implements. Codes 7 and 8 are int callbacks, still TODO on master.
  - Each PR's `ICastDeviceController.aidl`:
    - **#3570 and #3781:** connect/setListener/unregisterListener at `= 16/17/18`, which is correct.
    - **#3802:** off by one. It puts `stopApplication` at `= 3` (code 4), removes `sendMessage`, and moves connect to code 18. Excluded from integration.
  - **Gaps for W03:** setVolume `= 6`, setMute `= 7`, codes 4 and 6, listener codes 7, 8 and 15.
- 2026-10-01: Integration branch `cast/integration` in the VM clone, built from master + #3570 (peterhel, merge, includes #3567) + #3577 + #3554 (cherry-picks). No conflicts. `:play-services-core:assembleVtmDefaultDebug` running.
