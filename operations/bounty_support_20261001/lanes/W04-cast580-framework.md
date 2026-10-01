# W04 CAST580-FRAMEWORK (+ Roku): support lane for W01

Support lane for W01, the sole submitter of microg/GmsCore#580 (Google Cast). This lane delivers a branch and `git format-patch` files. It opens **no** PR, BountyHub claim or upstream comment.

## Listing states

Each state is kept separate.

| Listing | Reward | GitHub issue | PR (this lane) | Claim (this lane) | Merge | Payment |
|---|---|---|---|---|---|---|
| ef91cb1e: YouTube (stock + ReVanced), Crunchyroll, Netflix get a working session through microG | $100 funded, per dispatch. The SWE inventory in Slack lists #580 listing B as "$50 esc + $100 prom" (olofmogren). | microg/GmsCore#580 OPEN | none; W01 submits | none | none | none |
| 27c3cfe0: "cast so that e OS 3.x+ can cast to a Roku device" | $250 promised (emeitner) | microg/GmsCore#580 OPEN | none | none | none | none |

Competing upstream claim PRs listed in Slack: #3351, #3502, #3668, #3767. None of them is merged. I fetched their heads read-only. #3668 and #3767 change `CastMediaRouteController`, `CastDeviceControllerImpl` and `CastMediaRouteProvider` (play-services-cast core). None of them fixes the cast-framework dynamite binder layer described below.

## Owned files (in the microG GmsCore clone)

- `play-services-cast-framework/src/main/aidl/**` (cast framework binder interfaces)
- `play-services-cast-framework/core/**` (dynamite module: CastContextImpl, SessionManagerImpl, SessionImpl, CastSessionImpl, MediaRouterCallbackImpl, DiscoveryManagerImpl, new ReconnectionServiceImpl, new media/internal/FetchBitmapTaskImpl, new dynamite ModuleDescriptor)
- `play-services-core/.../chimera/container/DynamiteLoaderImpl.java`: removes the cast-framework "temp fix" version hack only. The new ModuleDescriptor replaces it.
- Shared, one line, separate commit: `play-services-cast/src/main/java/com/google/android/gms/cast/CastMediaControlIntent.java` (`categoryForCast(appId, namespaces)` was missing the `/`). W01 can drop this commit if W02 or W03 already touch the file.

I did not touch W02/W03 territory: `play-services-cast/core/**` (route provider, device controller, CASTV2 channel).

## Root cause: what apps' bundled cast-framework calls vs. what microG answered

Method: I decompiled `com.google.android.gms:play-services-cast-framework:22.3.1` and `play-services-cast:22.3.1` from dl.google.com (jadx 1.5.2). For every binder I compared the client proxy and stub transaction codes with microG's AIDL. Apps load microG's classes in-process through `DynamiteModule.load(..., "com.google.android.gms.cast.framework.dynamite")` and talk to them through `Binder.transact`. A code microG does not implement returns `false`, and the client then reads 0 or null.

Blocking defects found in microG (before this patch):

1. **No route event ever reached microG.** `CastContextImpl` never called `IMediaRouter.registerMediaRouterCallbackImpl` or `addCallback`, so `MediaRouterCallbackImpl` was dead code. Picking a device in the app's cast dialog never started a session.
2. **Session provider lookup always failed for current clients.** The client registers its CastSession provider under its own category string, `com.google.android.gms.cast.CATEGORY_CAST/<APPID>///ALLOW_IPV6` (or `/<APPID>/<ns,...>//ALLOW_IPV6`). microG recomputed `CATEGORY_CAST/<APPID>`, so `defaultSessionProvider` was `null` and the merged selector did not match the category the client and router use.
3. **Every client→module session notification was a no-op.** `ISession.notifySessionStarted/Ended/Resumed/FailedTo*/Suspended` were log-only, `endCurrentSession` and `startSession` were stubs, and `CastState` was stuck at `NO_DEVICES_AVAILABLE`. YouTube hides the cast button in that state.
4. **NPE on launch failure.** `SessionImpl.onApplicationConnectionFailure` nulled `castContext` and then dereferenced it.
5. Missing transaction codes for current clients:
   - ICastDynamiteModule code 7 (`newFetchBitmapTaskImpl` with context) and code 8 (`getSupportedVersion`)
   - ISession code 17 (`getSupportedVersion`) and code 18 (`getSessionStartType`)
   - ISessionProxy code 9 (route info update)
   - IMediaRouter codes 12–14
   - IMediaRouterCallback codes 7 (`getSupportedVersion`), 8, 9 and 10 (selected/connected/disconnected with requested route)
   - IFetchBitmapTask and its ProgressPublisher had empty AIDL
   - `ICastSession.onConnectionFailed` took `Status`, but the client sends `ConnectionResult`
6. `newReconnectionServiceImpl` and `newFetchBitmapTaskImpl` returned null. Media notification art never loaded, and the client ReconnectionService did nothing.

Transaction-code map (client 22.3.1 code = microG AIDL id + 1) after the patch:

| Interface | Client codes used | microG after patch |
|---|---|---|
| ICastDynamiteModule | 1,2,3,5,6,7,8 | all (4 = media notification, unused by current clients) |
| ICastContext | 1,3,5,6,11 | all, unchanged ids |
| ISessionManager | 1–9 | all; startSession/endCurrentSession implemented |
| ISession | 1–3,5–18 | all; notify* implemented |
| ISessionProxy (client stub) | 1–9 | 9 added (`onRouteInfoUpdated`) |
| ICastSession | 1–6 | `onConnectionFailed(ConnectionResult)` |
| ICastConnectionController (client stub) | 1–5 | unchanged |
| IMediaRouter (client stub) | 1–14 | 12–14 added |
| IMediaRouterCallback | 1–4,6–10 | all; microG reports `GMS_VERSION_CODE`, so new clients use code 8 for selection |
| ISessionManagerListener / ICastStateListener / IAppVisibilityListener (client stubs) | as before | used for events / foreground-background |
| IReconnectionService, IFetchBitmapTask(+Publisher) | 1–4 / 1 / 1–2 | implemented |

## What the patch implements

- **CastContextImpl**
  - Selector built from the client's own provider categories.
  - Registers the module callback with the client MediaRouter.
  - Requests discovery (`CALLBACK_FLAG_REQUEST_DISCOVERY`) while the app is visible, tracked through `Application.ActivityLifecycleCallbacks`. It drops to passive when the app is backgrounded, removing and re-adding the callback because MediaRouter only ORs flags.
  - Notifies `IAppVisibilityListener`.
  - Implements `setReceiverApplicationId` and `destroy`.
- **SessionManagerImpl**
  - Route selected → `provider.getSession()` → `SessionImpl.start` (onStarting → listeners → `proxy.start`).
  - `startSession(intent)` selects the route by id.
  - `endCurrentSession` → `proxy.end(stopCasting)`.
  - Route unselected ("Stop casting", `UNSELECT_REASON_STOPPED`) ends the session and stops the receiver app. Picking a different device ends the old session first.
  - `CastState` is computed from session state plus `isRouteAvailable(selector, IGNORE_DEFAULT_ROUTE)`.
  - Session recovery: saves route, session id and category; within 10 s of CastContext creation, if the provider `isSessionRecoverable()`, it re-selects the route and resumes (`proxy.onResuming`/`resume`, then `joinApplication`).
- **SessionImpl**: full state machine (starting / resuming / connected / suspended / ending / ended). All notify* methods are implemented and forwarded as SessionManagerListener events. It selects the default route on end or failure.
- **CastSessionImpl**:
  - `onConnected` → `launchApplication(appId, launchOptions)`, or `joinApplication(appId, sessionId)` when resuming or recovering from a suspend.
  - App connection success → `notifySessionStarted` or `notifySessionResumed(wasSuspended)`. Failure → start/resume failed or session ended, plus `closeConnection`.
  - `disconnectFromDevice` → `stopApplication(sessionId)` when stopCasting, then `closeConnection`.
- **ReconnectionServiceImpl**: keeps the client's ReconnectionService alive (`START_STICKY`) while a session is active. Otherwise it calls `stopSelf`.
- **FetchBitmapTaskImpl**: HTTP(S) image download with a size cap, a redirect limit and timeouts from the client, plus a downscale to the requested size. Used for media notification and controller artwork.
- **ModuleDescriptor** for `com.google.android.gms.cast.framework.dynamite` (version 1). This replaces the hard-coded `return 1` hack in DynamiteLoaderImpl.

## Interface boundary for W01 / W02 / W03 (what the framework now relies on)

- **W02 (route provider)**
  - Cast routes must carry `CastDevice` in the route extras (`com.google.android.gms.cast.EXTRA_CAST_DEVICE`) and have playback type remote. The client ignores non-remote routes.
  - Each route's control filters must contain the **exact category the app requests**, e.g. `com.google.android.gms.cast.CATEGORY_CAST/233637DE///ALLOW_IPV6` for YouTube. Matching is exact `IntentFilter.hasCategory`, so the provider has to echo the categories from the discovery request's selector, not a recomputed `categoryForCast(appId)`.
  - Route ids should be stable across app restarts for session recovery.
- **W03 (device controller / channel)**
  - The framework path is: client `CastSession` → `Cast.zza(...)` (client-side Cast API) → GmsCore `ICastDeviceController`. `launchApplication` and `joinApplication` must deliver `onApplicationConnectionSuccess(metadata, status, sessionId, wasLaunched)` or a failure code.
  - On `disconnectFromDevice(stopCasting)` the framework sends `stopApplication(sessionId)` and then `disconnect` on the same binder. The controller must send RECEIVER `STOP` before closing the socket.
- **W01**: integrate W02 + W03 + this patch and run on a device (see verification).

## Roku (listing 27c3cfe0): explicit achievable state

Sourced findings:

- Roku is not a Google Cast receiver. I found no Roku or third-party source saying any Roku OS supports Google Cast. Roku's casting help (https://support.roku.com/en-gb/article/360002990094) says "with supported apps like YouTube and Netflix … the supported app must be installed on both your mobile device and your Roku streaming device". That is app-to-app launch, not Cast.
- Roku exposes DIAL and ECP. Its ECP doc (https://developer.roku.com/docs/developer-program/dev-tools/external-control-api.md) says: "The Roku platform supports the DIAL (Discovery and Launch) protocol". ECP runs over HTTP on port 8060 (`launch/<id>`, `keypress`, `query/apps`, `input`). Discovery is `ST: roku:ecp`, and DIAL uses `urn:dial-multiscreen-org:service:dial:1`. The same doc says: "As of Roku OS 14.1, the Settings > System > Advanced system settings > Control by mobile apps feature must be set to "Enabled"".
- YouTube's phone→Roku path is DIAL plus YouTube's own Lounge session: SSDP, `…:8060/dial/YouTube`, then a Lounge pairing (https://github.com/yuliskov/MediaServiceCore/issues/10, https://github.com/iBicha/playlet). Netflix likewise uses DIAL (co-developed by Netflix and YouTube; https://www.howtogeek.com/215791/ "Even the Roku has support for DIAL, making it possible to cast YouTube and Netflix to any TV with a Roku").
- microG's Cast discovery is mDNS `_googlecast._tcp` only (`play-services-cast/core/.../CastMediaRouteProvider.java`). Chromium's Media Router doc (https://www.chromium.org/developers/design-documents/media-router/) says its DIAL provider is "implemented only in desktop Chrome and ChromeOS".
- UNSOURCED: a primary source that Google Play services on Android ships no DIAL route provider. Also unsourced: Crunchyroll Android casting to Roku. Search summaries only say Chromecast / Android TV.

Achievable state:

- Google Cast apps (Crunchyroll's Cast SDK path, Netflix/YouTube Chromecast path) **cannot** reach a Roku through microG's Cast implementation, because Roku does not speak CASTV2. A generic Cast-SDK-app→Roku bridge would need a Roku-side receiver channel and a protocol translator. That is outside Google Cast and outside microG.
- YouTube and Netflix reach Roku through their **own** in-app DIAL/second-screen code. The sources point that way, but it is inferred, not proven by a GMS binary. What microG must do for that path is not break it. A working `CastContext` matters here: when `CastContext.getSharedInstance` fails, the client logs "Failed to load module from Google Play services. Cast will not work properly" and apps fall back. This patch makes CastContext initialise and reports a correct `CastState`.
- I implemented nothing Roku-specific in microG and did not request DIAL/SSDP discovery from W02. It does not legitimately belong in microG's Cast scope. The 27c3cfe0 acceptance text ("e OS 3.x+ can cast to a Roku device") is achievable only to the extent the apps' own DIAL paths work on /e/OS with a functioning CastContext. **Device verification of that on /e/OS + a Roku is UNVERIFIED** (no device here).

## Verification (what was actually run)

- Clone: `~/work/GmsCore` (microg/GmsCore master `32bc8954`, 2026-09-29), branch `cast-framework-session`.
- `./gradlew :play-services-cast-framework-core:compileReleaseJavaWithJavac` → exit 0.
- `./gradlew :play-services-core:assembleHmsDefaultDebug` → exit 0, `com.google.android.gms-252432035.apk` (106 MB). dexdump confirms that `CastContextImpl`, `ReconnectionServiceImpl`, `FetchBitmapTaskImpl` and the cast framework `ModuleDescriptor` are in the APK.
- `git am` of both patches onto a clean `32bc895` worktree → applies; the resulting tree is identical to the lane branch.
- Not run: on-device casting with YouTube, ReVanced, Crunchyroll or Netflix to a Chromecast, or with a Roku. This container has no Android device or emulator (no `/dev/kvm`). The session flow above is grounded in the decompiled 22.3.1 client code, not in a device run. W01 owns the device run.

## Deliverables

- Branch (local clone `~/work/GmsCore`, not pushed anywhere; no woahwhattheheck/GmsCore fork exists): `cast-framework-session`. Commits: `e34dc7e` Cast: implement cast framework session lifecycle (21 files, +1004/−205); `13c6031` Cast: fix categoryForCast with namespaces. Base: `32bc895`. Author `woahwhattheheck <293286387+woahwhattheheck@users.noreply.github.com>`; no trailers.
- Patches: `operations/bounty_support_20261001/lanes/W04-cast580-framework/*.patch` (`git am` onto microg/GmsCore master `32bc8954`)

## Next action

W01: apply the patches (`git am`) together with the W02/W03 changes. Make sure the W02 provider echoes the requested `CATEGORY_CAST/...` categories (boundary above). Then build and run YouTube against a Chromecast. If the W02 or W03 lane already changes `CastMediaControlIntent.java`, drop patch 0002.
