# W02 CAST580-DISCOVERY — support lane for W01 (microg/GmsCore#580)

Updated 2026-10-01 (round 3). Support lane: no PR, BountyHub claim, or upstream comment from here. W01 integrates and submits. The fork woahwhattheheck/GmsCore now exists (per root); this lane still hands over patches only.

## State per listing

| Listing | Advertised / funded / promised (from SWE sweep in the orders thread) | GitHub issue | PR | Claim | Merge | Payment |
|---|---|---|---|---|---|---|
| 27c3cfe0 and ef91cb1e (#580; the thread names them A = $250 promised, emeitner, and B = $50 escrowed + $100 promised, olofmogren; I did not map the ids to A and B) | A $250 / $0 / $250; B $150 / $50 / $100 | microg/GmsCore#580 OPEN | none from this team (W01 owns submission) | none | none | none |

## Round 3 (2026-10-01): verification results and incremental fixes

**State: DELIVERED TO W01** as incremental patches, as W01 asked. 0003 and 0004 are not rewritten.

W01 is fixing four controller defects on top of fda4a03b in its own commit, "Cast: Fix route controller state ordering, reconnect and mute handling", and asked W02 not to touch them:
- F1: CONNECTED is posted after DISCONNECTED.
- F2: no reconnect while the route is selected.
- F3: setting the volume does not unmute.
- F4: a status without a volume level is published as volume 0.

### Patches (in `operations/bounty_support_20261001/lanes/W02-patches/`)

| Patch | Parent | Commit (W02 VM `~/work/GmsCore`) | Files |
|---|---|---|---|
| `0005-Cast-Harden-route-discovery.patch` | fda4a03b | `81e41f22` | `CastMediaRouteProvider.java` |
| `0006-Cast-Track-route-connection-state-per-route-controll.patch` | 81e41f22 | `a373b04c` | `CastMediaRouteProvider.java`, `CastMediaRouteController.java` (6 call sites) |
| `followup/0001-Cast-Implement-remote-playback-control-requests.patch` | a373b04c | `2ce228b5` | 0004 rebased onto 0006. The only change is the same 6 call sites in the new controller, `provider.onRouteStateChanged(routeId,` → `provider.onRouteStateChanged(CastMediaRouteController.this, routeId,`. |
| `followup/0002-Cast-Fix-remote-playback-session-and-command-orderin.patch` | 2ce228b5 | `ff677ea9` | `CastRemotePlayback.java`, `CastMediaRouteController.java`. It also applies unchanged with `git am --3way` on the original 0004 `8f133286` (checked, exit 0). |
| `series/0001..0012` | 32bc8954 | ..`ff677ea9` | The whole chain. `git am` onto a clean 32bc8954 exits 0, and the tree is byte-identical to `ff677ea9`. |

**First PR stack.** W01's tree (…fda4a03b), then W01's controller fix, then 0005, then 0006.
- 0005 touches only the provider, so it should apply on W01's fix.
- 0006 changes the six `provider.onRouteStateChanged(routeId, …)` calls in the controller to pass the controller first. If they conflict with W01's F1/F2 lines, resolve mechanically: every `provider.onRouteStateChanged(routeId,` becomes `provider.onRouteStateChanged(CastMediaRouteController.this, routeId,`.

**Follow-up PR stack.** followup/0001 (0004 rebased), then followup/0002.

### What 0005 fixes (CastMediaRouteProvider)

Sources: the W02 workflow, and items in W01's `series-review-2026-10-01.json`.
- **getAttributes() on API 19/20 (high).** `NsdServiceInfo.getAttributes()` is API 21. The guard was SDK 16 and the NewApi lint check was suppressed, so GmsCore crashed on API 19 and 20. Discovery now requires API 21, all `@SuppressLint("NewApi")` are removed, and lint checks the guard: lintDebug on cast-core reports 0 errors.
- **Stalled resolves.** A resolve now gives up after 15 s (`stopServiceResolution` on API 34+), and late callbacks are ignored. Before this, one hung resolve stopped every later device from being resolved.
- **Duplicate resolves.** A service found several times is queued once.
- **Discovery start/stop failures.** A failed stop is treated like a stop, since NsdManager drops the listener either way. A failed start is retried with backoff from 1 s to 60 s while discovery is wanted.
- **Stale routes.** When a discovery run of at least 10 s stops, disconnected routes not found again during it are dropped.
- **Group bit.** `ca` bit 32 (multizone group) is kept in `CastDevice` capabilities.

### What 0006 fixes

MediaRouteProviderService creates one controller per client and route. Before, one app's unselect published the shared route as disconnected (and removed it if the device was gone) while another app was still connected. The provider now keeps the state per controller and publishes CONNECTED if any controller is connected, CONNECTING if any is connecting, and DISCONNECTED otherwise.

### What followup/0002 fixes (remote playback)

- **END_SESSION then PLAY.** The PLAY attached to the receiver application that was being stopped (a STOPPING state now prevents this). END_SESSION during a launch now stops the application once it attaches.
- **Commands during launch or load.** PAUSE, RESUME, STOP and SEEK sent while the item is launching or loading are deferred until the LOAD reply. Before, they were acknowledged without effect.
- **Status updates.** Status changes caused by our own requests, END_SESSION, and START_SESSION replacing a session are now sent to the status update receivers.
- **START_SESSION.** It stops the replaced session's media, including a LOAD still in flight, and reports the old item CANCELED.
- **LOAD failures.** A failed LOAD no longer overwrites CANCELED or INVALIDATED with ERROR. Failures now say whether the request timed out, could not be sent, or lost the connection; before, everything read "timed out".
- **Stop casting.** UNSELECT_REASON_STOPPED stops the remote-playback receiver application.
- **Robustness.** A wrong-type PendingIntent extra no longer crashes GmsCore with a ClassCastException. `setRemoveOnCancelPolicy` is guarded to API 21+.

### Runs (W02 VM)

- **cast-core compile and lint.** `./gradlew :play-services-cast-core:compileDebugJavaWithJavac :play-services-cast-core:lintDebug` exit 0 at 81e41f22, a373b04c and ff677ea9. cast-core lint reports 0 errors at each; warnings are 9 at 81e41f22 and a373b04c.
- **Tip build at ff677ea9.**
  - Command: `./gradlew :play-services-core:assembleVtmDefaultDebug :play-services-cast:lintDebug :play-services-cast-core:lintDebug :play-services-cast-framework:lintDebug :play-services-cast-framework-core:lintDebug`, exit 0.
  - Output: `com.google.android.gms-252432035.apk` (106,840,875 bytes).
  - Lint: 0 errors in all four modules. Warnings are cast 4, cast-core 9, cast-framework 9, cast-framework-core 3.
  - dexdump: 0 `Lsu/litvak` and 0 `Lorg/codehaus` classes. `CastRemotePlayback`, `CastMediaRouteController`, `CastMediaRouteProvider`, `CastChannelRegistry` and `channel/CastDeviceSession` are present.
- **Host protocol run.** The real compiled `CastRemotePlayback` plus W03's `CastDeviceSession`/`CastChannel` classes ran on a JVM against a scratch software CastV2 receiver: TLS, framing, deviceauth, receiver namespace, and the Default Media Receiver media namespace. The driver mirrors the controller's PlaybackConnection and SessionCallbacks wiring.
  - At followup/0002 (ff677ea9 classes): 63 checks PASS, `SUMMARY failures=0`, exit 0 on 3 of 3 runs.
  - At the original 0004 (8f133286 classes): exit 1 with 6 failures. These are exactly the fixed defects: END_SESSION followed by PLAY, STOP during LOAD, PAUSE during LOAD, START_SESSION leaving media playing, no END_SESSION update, and the "timed out" wording on connection loss.
  - Other scenarios passed at both commits: launch, LOAD with metadata, broadcasts, pause/resume/seek/getStatus, item replacement, LOAD_FAILED, FINISHED, another sender replacing the application (status-first and close-first), wrong session/item ids, setVolume 0.35 round trip, END_SESSION STOP, and receiver killed mid-request (fails within 20 ms, INVALIDATED, onDisconnected(7)).
  - The receiver and driver are scratch tools in the W02 VM scratchpad and are not committed (RULES 17).
- **Not covered by the host run.** Android glue: PendingIntent sending, the Bundle/MediaItemStatus conversion, the main-thread ControlRequestCallback, the provider and NSD, and MediaRouter selection. Device behaviour beyond the scratch receiver's approximation of the Default Media Receiver. **No real Chromecast or emulator run.**

### Findings in W01's F1-F4 area, passed to W01 and not patched by W02

All were confirmed by two adversarial verifiers each.
- **(i) Volume echo.** A RECEIVER_STATUS replying to an older SET_VOLUME overwrites the local volume, so rapid volume-key presses lose steps (`CastMediaRouteController` onDeviceStatusChanged).
- **(ii) Placeholder volume.** onUpdateVolume applies the delta to the VOLUME_MAX/2 placeholder before the device volume is known.
- **(iii) Dead registry sessions.** onSetVolume's CastChannelRegistry fallback can pick dead sessions that CastDeviceControllerImpl leaked. This is the same root cause as W01's death-link and leak items.

## Integration handoff to W01 (2026-10-01, round 2): controller on CastDeviceSession + remote playback

**State: DELIVERED (interim).** Verification is still running (a host protocol run against a software receiver, plus bug hunts). If it turns up fixes, they come as an updated 0003/0004 and series, recorded here.

**Local branch.** `cast/series-w02` in `~/work/GmsCore` (W02 VM), HEAD `8f133286`. Parent chain:

| # | Commit | Patch | Lane |
|---|---|---|---|
| base | `32bc8954` | microg/GmsCore master | - |
| 1 | `a22a6af7` | W02 0001 Keep status in CastDevice and skip icon without path | W02 |
| 2 | `94e9732e` | W02 0002 Fix device discovery and route publication | W02 |
| 3 | `3b041680` | W03 0001 Add CastV2 channel to talk to receivers directly (`git am --3way`, unchanged) | W03 |
| 4 | `4e44d92d` | W03 0002 Implement the device controller on the CastV2 channel (unchanged) | W03 |
| 5 | `db991126` | W04 0001 implement cast framework session lifecycle (unchanged) | W04 |
| 6 | `36e6bfda` | W04 0002 fix categoryForCast with namespaces (unchanged) | W04 |
| 7 | `42964640` | **W02 0003** Run the media route controller on the CastV2 session | W02 |
| 8 | `fda4a03b` | **W03 0003 minus its `CastMediaRouteController.java` hunk** (see below) | W03 |
| 9 | `8f133286` | **W02 0004** Implement remote playback control requests | W02 |

**Patch files** (in `operations/bounty_support_20261001/lanes/W02-patches/`):
- `0003-Cast-Run-the-media-route-controller-on-the-CastV2-se.patch`: commit 7. Changes `play-services-cast/core/src/main/java/org/microg/gms/cast/CastMediaRouteController.java`.
- `W03-0003-Cast-Drop-chromecast-java-api-v2-minus-controller-hunk.patch`: commit 8. This is W03's patch with its `CastMediaRouteController.java` hunk removed, because 0003 already rewrites that file without any `su.litvak` import. It also has a reworded commit message (the old one described the controller hunk), and its author is W03's placeholder. It changes:
  - `play-services-cast/core/build.gradle` (drops `info.armills.chromecast-java-api-v2`);
  - `play-services-core/src/main/java/org/microg/gms/ui/AboutFragment.java` (drops the library line).
- `0004-Cast-Implement-remote-playback-control-requests.patch`: commit 9. Changes:
  - `play-services-cast/core/src/main/java/org/microg/gms/cast/CastMediaRouteController.java`;
  - new `play-services-cast/core/src/main/java/org/microg/gms/cast/CastRemotePlayback.java`.
- `series/0001..0009`: the whole chain above as one `git format-patch 32bc8954..8f133286`.

Apply either set onto `32bc8954` with `git am`:
- `series/*`, or
- W02 0001-0002, then W03 0001-0002, then W04 0001-0002, then W02 0003, then `W03-0003-...-minus-controller-hunk`, then W02 0004.

Both orders exit 0, and the resulting tree is byte-identical to `8f133286` (checked with `git am` in a fresh worktree and a tree-hash compare).

**What 0003 does (W01 interface 3)**
- `onSelect` opens a W03 `CastDeviceSession(address, servicePort or 8009)`. The provider reports CONNECTING, then CONNECTED from `onConnected`, and DISCONNECTED on `onConnectionFailed`, `onDisconnected`, unselect or release.
- It follows `RECEIVER_STATUS` volume (`level * 20`) into the route descriptor.
- `onSetVolume` / `onUpdateVolume` send `SET_VOLUME` (`level = v / 20`):
  - through the route's own session when it is connected;
  - otherwise through `CastChannelRegistry.get(routeId)`;
  - otherwise through the session that is still connecting (queued until it is up).
- Callbacks from a replaced session are ignored.
- No `su.litvak` import is left anywhere.

**What 0004 does.** Before this patch, routes advertised remote-playback actions and `onControlRequest` returned false for all of them.
- It implements `MediaControlIntent` PLAY, SEEK, GET_STATUS, PAUSE, RESUME, STOP, START_SESSION, GET_SESSION_STATUS and END_SESSION on the Default Media Receiver `CC1AD845`, over the route's session and the media namespace (`LOAD`/`SEEK`/`GET_STATUS`/`PAUSE`/`PLAY`/`STOP`).
- Result bundles carry session and item ids and statuses as `RemotePlaybackClient` expects. Item and session status updates go to the client's PendingIntents.
- Ending the session stops the receiver app.
- Protocol logic lives in plain Java plus `org.json` (`CastRemotePlayback`) and runs on a per-route executor. Results are posted back to the main thread.
- This is a separate patch, so W01 can leave it out of the first submission.

**Runs (W02 VM, JDK 21, SDK 35 / build-tools 35.0.0, Gradle 8.13, Google Maven Central mirror via `~/.gradle/init.d`):**
- `./gradlew :play-services-cast-core:compileDebugJavaWithJavac` at 42964640: exit 0. This is a separate worktree, so commit 7 compiles without commit 8.
- `./gradlew :play-services-core:assembleVtmDefaultDebug :play-services-cast:lintDebug :play-services-cast-core:lintDebug :play-services-cast-framework:lintDebug :play-services-cast-framework-core:lintDebug` at fda4a03b: exit 0.
  - APK `com.google.android.gms-252432035.apk` (106.8 MB).
  - Lint errors are 0 in all four modules. Warnings: cast 4, cast-core 10, cast-framework 9, cast-framework-core 3.
  - dexdump of the APK: 0 `Lsu/litvak` classes and 0 `Lorg/codehaus` classes. `CastMediaRouteController`, `CastMediaRouteProvider`, `CastChannelRegistry` and `channel/CastDeviceSession` are present.
- `./gradlew :play-services-cast-core:compileDebugJavaWithJavac` at 8f133286: exit 0. The full APK and lint at 8f133286 come with the verification round.
- **Not run on a device.** There is no Chromecast and no emulator (no `/dev/kvm`). The device run on Bryce's LAN stays W01's owner blocker.

**Cross-lane notes**
- dot's frame-harness finding (thread, `BH-CAST-580-FRAME-HARNESS`) is about the unbounded frame length in the old `chromecast-java-api-v2` `Channel.read`.
  - W03 0003 removes that library from the build.
  - W03's `CastChannel.kt:183-184` already rejects lengths below 0 or above `MAX_PAYLOAD_SIZE + 4096` before allocating, and reads the body with `readFully` (EOF raises `EOFException`).
- `BH-CAST-IMPLEMENT-580` (Commons Grok worker) overlaps W01–W04. W03 already flagged it for the coordinator, and W01 remains the sole submitter.

## Deliverable: branch and patches

- Local clone: `~/work/GmsCore`, branch `cast-discovery-routes`. Base is upstream master `32bc8954ff872d0e1a05ddfae81561b6dbecef69`. Head is `94e9732e`.
- Patches are in this repo at `operations/bounty_support_20261001/lanes/W02-patches/`:
  - `0001-Cast-Keep-status-in-CastDevice-and-skip-icon-without.patch`: `play-services-cast/.../CastDevice.java`, +5/−1.
  - `0002-Cast-Fix-device-discovery-and-route-publication.patch`: `CastMediaRouteProvider.java` and `CastMediaRouteController.java`.
- Commit author is `woahwhattheheck <293286387+woahwhattheheck@users.noreply.github.com>`. Messages are technical only, with no trailers.
- Checks I ran:
  - `git am` of both patches onto a clean `origin/master` exited 0, and the result is byte-identical to the branch.
  - `./gradlew :play-services-cast-core:compileDebugJavaWithJavac :play-services-cast:compileDebugJavaWithJavac` exited 0.
  - `./gradlew :play-services-cast-core:assembleDebug :play-services-cast:assembleDebug` exited 0 (Android SDK 35, build-tools 35.0.0, Gradle 8.13).
  - Maven Central returned 429 in this container, so I built through a local init script, `~/.gradle/init.d/central-mirror.gradle`, that points to Google's Maven Central mirror. The repo itself is unchanged.
- **Not run on a device.** The container has no `/dev/kvm`, so no emulator, and no Cast receiver on its network. Discovery, select and volume have not been tried against real hardware. W01 or Bryce should confirm on a phone with a Chromecast before or with submission.

## What the patches change (owned files)

**`play-services-cast/core/src/main/java/org/microg/gms/cast/CastMediaRouteProvider.java`**
- **Discovery starts more often.** It now runs on any valid discovery request whose selector contains a Cast or remote-playback category. Before, it only ran on `isActiveScan()`, but the Cast framework and MediaRouter request passive discovery. So master finds no devices until a chooser forces an active scan.
- **App categories are collected properly.**
  - `CATEGORY_CAST/<appId>` and `CATEGORY_CAST_REMOTE_PLAYBACK/<appId>` are now collected from every request into a Set. They used to go into a list with duplicates, and only during active scans.
  - Routes are republished when the categories change. This is the point wborn raised reviewing upstream #3354.
- **The NSD start/stop state machine is fixed.**
  - Each run uses a new listener.
  - A request that arrives while a start or stop is still pending is applied from the callback. On master it was lost: if a stop was requested during `DISCOVERY_REQUESTED`, discovery never stopped.
- **Resolves are serialized.** Found services go into a queue and resolve one at a time, and `FAILURE_ALREADY_ACTIVE` is retried after 500 ms. On master, the second and later devices found in a burst were dropped.
- **TXT parsing tolerates missing records.**
  - Only `id` is required. `fn` falls back to the service name.
  - `ca` is now read as the capability bitmask (master hardcoded video+audio out). Bit 32 marks a multizone group.
  - A missing `ic`, `st` or `md` no longer drops the device through an NPE.
- **Known devices are updated** with the latest resolved record (address, port, name, status). Master kept the first one forever.
- **Threading.** All state lives on the main thread. On master, NSD binder threads mutated HashMaps while `publishRoutes` iterated them (the ConcurrentModificationException in upstream #2449 / #3354).
- **Route descriptor changes.**
  - Device type is TV when the device has video out and is not a group, otherwise SPEAKER.
  - `PLAYBACK_VOLUME_VARIABLE`, max 20, using the volume the controller tracks. Master had FIXED with volume 0.
  - The connection state is published from the controller.
  - The duplicated `ACTION_SYNC_STATUS` filter is removed.
- **Lost routes.** A route that is in use is kept when its service is lost, and removed when its controller disconnects.
- **New package-private API** (used by the controller): `onRouteStateChanged(routeId, connectionState, volume)`, where `-1` keeps a value, and `VOLUME_MAX`.

**`play-services-cast/core/src/main/java/org/microg/gms/cast/CastMediaRouteController.java`**
- The constructor is now `(provider, routeId, address, port, initialVolume)` and uses `new ChromeCast(address, port)`. Groups announce ports other than 8009.
- **Select.** `onSelect` publishes CONNECTING, then on a single-thread executor it:
  - connects;
  - registers a spontaneous-event listener;
  - reads `getStatus().volume`;
  - publishes CONNECTED with that volume. If anything fails it publishes DISCONNECTED.
- **Unselect and release.** `onUnselect(int)` and `onRelease` disconnect off the main thread. `onRelease` also shuts the executor down.
- **Volume.**
  - `onSetVolume` and `onUpdateVolume` call `chromecast.setVolume(v/20f)`.
  - STATUS events update the route volume when it is changed on the device.
- `onControlRequest` is unchanged: it still returns false. Remote-playback control intents are not in this lane. If W03 or W01 wants them handled, this is the hook.

**`play-services-cast/src/main/java/com/google/android/gms/cast/CastDevice.java`**: the discovery constructor now stores `status`, and adds an icon only when `ic` is present. This is a two-line change in a shared file, kept as a separate patch (0001) so W01 can drop it if W03 or W04 also edit this file.

## Interface boundary (assumed)

W01's lane file was not on `origin/claude/bh-20261001-w01-cast580-owner` when this was written; the branch did not exist yet. Neither did W03's or W04's. So this is the boundary I assumed:

- **W02 owns** `CastMediaRouteProvider`, `CastMediaRouteController` and `CastMediaRouteProviderService` (unchanged), plus the CastDevice constructor lines above.
- **The contract to the framework (W04) and the device controller (W03)** is unchanged:
  - route id is `CastDevice.getDeviceId()`;
  - the route extras carry the CastDevice via `CastDevice.putInBundle`, read with `CastDevice.getFromBundle`;
  - routes match `CastMediaControlIntent.categoryForCast(appId)` selectors.
- **For W03.** `CastDeviceControllerImpl` (not touched here) still calls `new ChromeCast(castDevice.getAddress())` and ignores `castDevice.getServicePort()`. Sessions to multizone groups will fail until it uses `new ChromeCast(address, servicePort)`. That is a one-line change in W03's file.
- **DIAL/SSDP (Roku).** Not implemented. There was no W04 lane file asking for it. If W04 asks, it would be a separate provider and should not go into this patch.

## Findings for W01 (upstream context)

- **AI-generated PRs get labelled and closed.** mar-v-in labelled Cast PRs #3767 and #3417 "AI slop" ("Pull requests that have been created using AI") and closed them; #3767 was closed 2026-09-09. Every upstream submission for #580 runs into this maintainer policy. W01 and Bryce need to decide how to handle the AI-use question and disclosure before submitting.
- **Open upstream PRs that overlap these files:**
  - #3354 (koczadly): thread safety in the provider, reviewed by wborn. That review asks for categories from every valid request and a republish on change, which patch 0002 does.
  - #3502: provider refactor plus VARIABLE volume, with the initial volume still 0. Its PR page returns 404 anonymously.
  - #3351 and #3668: controller select/volume.
  - #3470: moves socket I/O off the main thread.
  - None of these is merged. The last master change to the provider was 2023-09-21.
- I could not read the #580 comment thread: the GitHub MCP tools in this session are scoped to the commons repo, and the issue page loads comments lazily.

## Next action

W01: take patches 0001 and 0002 into the integration branch (`git am`), and run them on a device with a Chromecast or Google Home. Check that:

- devices show in the route chooser without an active scan;
- several devices all appear;
- the volume slider works.

W02 is idle and ready for follow-up asks from W01, W03 or W04 (port fix, DIAL provider, `onControlRequest`).
