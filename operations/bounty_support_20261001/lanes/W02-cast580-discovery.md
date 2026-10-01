# W02 CAST580-DISCOVERY — support lane for W01 (microg/GmsCore#580)

Updated 2026-10-01. Support lane: no PR, BountyHub claim, or upstream comment from here. W01 integrates and submits.

## State per listing

| Listing | Advertised / funded / promised (from SWE sweep in the orders thread) | GitHub issue | PR | Claim | Merge | Payment |
|---|---|---|---|---|---|---|
| 27c3cfe0 and ef91cb1e (#580; the thread names them A = $250 promised, emeitner, and B = $50 escrowed + $100 promised, olofmogren; I did not map the ids to A and B) | A $250 / $0 / $250; B $150 / $50 / $100 | microg/GmsCore#580 OPEN | none from this team (W01 owns submission) | none | none | none |

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
