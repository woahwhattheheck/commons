On current master, apps that use the Cast SDK (`CastContext`) load microG's `com.google.android.gms.cast.framework.dynamite` module. That module is mostly stubbed:
- routes never reach a session;
- `CastState` stays at `NO_DEVICES_AVAILABLE`, so apps hide their cast button;
- the device controller can't join, register namespaces or set volume, and it doesn't implement the connectionless API that current SDKs use.

This PR implements the whole path: discovery, the device connection, and the framework session.

### Device connection (`play-services-cast/core`)
- **In-tree CastV2 channel** (`channel/CastChannel.kt`, `channel/CastDeviceSession.kt`, `cast_channel.proto` via Wire). It replaces `chromecast-java-api-v2`. It handles:
  - TLS, length-prefixed `CastMessage` framing and the deviceauth challenge;
  - per-transport virtual connections and heartbeat;
  - receiver status, launch/join/leave/stop and volume/mute;
  - text and binary messages on the application's transport.
- **`CastDeviceControllerImpl`** serves every `ICastDeviceController` transaction the current client SDK sends: disconnect, leave, stop, requestStatus, setVolume, setMute, sendMessage, sendBinaryMessage, register/unregister namespace, launch, join, connect, addListener and removeListener. It supports both client flows:
  - the legacy flow, with the listener in the service request extras and reconnect via `last_application_id`;
  - the connectionless flow (`addListener`, then `connect`, then `onConnectedWithResult`).

  A death link on the client's listener tears the connection down when the app dies. The client may reuse the controller binder after disconnecting, and the controller reopens in that case.
- **`CastServiceImpl`** answers `CAST_API` (161) requests. The bind advertises the features the client checks for: `cxless_client_minimal`, `module_flag_control` and the others.
- **`CastMediaRouteProvider`**:
  - discovery runs on passive requests too;
  - resolves are serialized, with a timeout on API 34+;
  - TXT records are parsed tolerantly;
  - the exact requested `CATEGORY_CAST/<appId>...` categories are echoed in the control filters;
  - routes have variable volume and expire when discovery stops, unless they are still in use;
  - all state is confined to the main thread.
- **`CastMediaRouteController`** follows and sets the device volume over its own CastV2 session. It reconnects on demand if that connection drops while the route stays selected.

### Cast framework module (`play-services-cast-framework/core`)
- **`CastContextImpl`**:
  - builds the merged selector from the app's own session provider categories;
  - registers the module's callbacks with the app's MediaRouter;
  - drives active discovery while an activity of the app is started;
  - implements `setReceiverApplicationId` and `destroy`.
- **`SessionManagerImpl` / `SessionImpl` / `CastSessionImpl`**:
  - session start on route selection, plus `startSession` and `endCurrentSession(stopCasting)`;
  - the session state machine and all `SessionManagerListener` events;
  - `CastState` transitions;
  - launch or join of the receiver application, and resume of a saved session after the app restarts.
- **`ReconnectionServiceImpl`**, **`FetchBitmapTaskImpl`** (notification and controller artwork) and a `ModuleDescriptor` for the dynamite module. The `return 1` placeholder in `DynamiteLoaderImpl` is removed.

### Binder and parcel compatibility
I checked the transaction codes and argument types of these interfaces against the `play-services-cast` / `play-services-cast-framework` 22.3.1 client libraries:
- `ICastDeviceController` and its listener;
- `ICastDynamiteModule`, `ICastContext`, `ISessionManager`, `ISession`, `ICastSession`;
- `IMediaRouter` and its callback;
- `ISessionProxy` and the fetch-bitmap interfaces.

Two changes come out of that:
- `ICastSession.onConnectionFailed` now takes the `ConnectionResult` the client sends.
- New codes such as `getSupportedVersion` are implemented.

`CastDevice`, `LaunchOptions`, `ApplicationMetadata` and the status parcels already use the client's SafeParcel field ids.

### Testing
- `./gradlew :play-services-core:assembleVtmDefaultDebug :play-services-core:assembleVtmDefaultRelease` succeeds.
- `lintDebug` on `play-services-cast`, `play-services-cast-core`, `play-services-cast-framework` and `play-services-cast-framework-core` reports 0 errors.
- The compiled `CastChannel` / `CastDeviceSession` classes were run on the JVM against a software CastV2 receiver. Every step passed:
  - TLS, device authentication and virtual connections;
  - heartbeat over 25 s idle;
  - launch, join by app and by session id, and launch with `relaunchIfRunning=false` joining the running instance;
  - leave, stop and relaunch;
  - volume and mute;
  - text, binary and media namespace messages, with unregistered namespaces filtered;
  - the payload limit, a refused platform namespace, and an unknown app id;
  - the receiver dying mid-session.
- Not yet tested on a phone against a physical Chromecast. The binder layer and the cast framework module have not been run on a device.

### Known limitations
- A dropped connection ends the cast session. Play services instead suspends it and reconnects.
- Cast Connect launch options (`androidReceiverCompatible`, credentials) are not forwarded to the receiver.
- MediaRouter remote-playback control intents (`RemotePlaybackClient`) are still unhandled; this is planned as a follow-up.
- Discovery needs API 21 (`NsdServiceInfo.getAttributes`). Below API 34 a stuck resolve cannot be cancelled.
- The deviceauth signature is not verified, which matches master.

Related open PRs on the same files: #3351, #3354, #3377, #3470, #3505, #3554, #3567, #3570, #3577, #3668, #3781, #3802.

Closes #580
