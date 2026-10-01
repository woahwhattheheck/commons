# W03 host CastV2 run on W01's final code (commons 1b72e8be8)

## Tree
- `git worktree add wt-final 32bc8954`
- `git am` of `patches/W01/submit/0001-0008`: exit 0
- `git apply 0009`: exit 0
- `git apply 0010`: exit 0
- The staged diff against 32bc8954 is identical to `patches/W01/submit-full.diff`, ignoring `index` lines (38 files, +3048/-790).

## Build
- `./gradlew --no-daemon --max-workers=3 --no-configuration-cache -q :play-services-cast-core:compileDebugJavaWithJavac`: exit 0 on the first try. JDK 21, SDK 35.

## Run setup
- Classpath: `wt-final/play-services-cast/core/build/tmp/kotlin-classes/debug`, wire-runtime-jvm 6.4.6, okio-jvm 3.17.0, kotlin-stdlib 2.2.21 and org.json 20240303.
- The drivers call the public `CastDeviceSession` API. That API is unchanged in the final code, so the drivers needed no adaptation.
- Receiver: `python3 receiver.py <port> cert.pem key.pem`. It speaks TLS with the real CastMessage framing and handles deviceauth, connection, heartbeat and the receiver namespace, plus per-app transports with an echo namespace and the media namespace.
- The receiver and drivers are scratch tools and are not committed.

## Drive (full protocol), `timeout 150 java -cp out-final:$CP Drive 18030`, exit 0
    OK   connectionFailed 7
    OK   connected
    OK   deviceStatus level=1.0 muted=false apps=0 active=1 standby=0
    OK   appConnected E1C0DE01 launched=true
    OK   sendOk urn:x-cast:com.example.echo 101
    OK   text urn:x-cast:com.example.echo {"echo": {"n": 1}}
    OK   appStatus Echoed 1
    OK   sendOk urn:x-cast:com.example.echo 102
    OK   binary urn:x-cast:com.example.echo cba
    OK   sendOk urn:x-cast:com.google.cast.media 103
    OK   text urn:x-cast:com.google.cast.media {"type": "MEDIA_STATUS", "requestId": 7
    OK   text urn:x-cast:com.google.cast.media {"type": "MEDIA_STATUS", "requestId": 0
    OK   sendOk urn:x-cast:com.google.cast.media 108
    OK   unregistered namespace not delivered
    OK   deviceStatus level=0.4 muted=false
    OK   deviceStatus level=0.4 muted=true
    OK   appConnected E1C0DE01 launched=false session=7975dfcf-3a34-4b32-b30e-d2cef558faa2
    OK   appConnectionFailed 2004
    OK   sendFail urn:x-cast:com.google.cast.tp.connection 104 2001
    OK   sendFail urn:x-cast:com.example.echo 105 2006
    OK   leaveResult 0
    OK   sendFail urn:x-cast:com.example.echo 106 2005
    OK   appConnected E1C0DE01 launched=false session=7975dfcf-3a34-4b32-b30e-d2cef558faa2
    OK   appDisconnected 2005
    OK   appConnected E1C0DE01 launched=true
    OK   sendOk urn:x-cast:com.example.echo 107
    OK   text urn:x-cast:com.example.echo {"echo": {"n": 3}}
    OK   appDisconnected 0
    OK   stopResult 0
    ALL OK
- Heartbeat during the 25 s idle step: 5 PING from the sender and 5 PONG back.

## Drive2 (receiver process killed mid-session), `java -cp out-final:$CP Drive2 18031` then `kill <receiver pid>`, exit 0
    connected
    appConnected CC1AD845
    disconnected 7

## Drive3 (CAST-CH-1), `timeout 60 java -cp out-final:$CP Drive3 18032`, exit 0
Session A launches E1C0DE01 and leaves. Session B then calls connect() and immediately launchApplication(E1C0DE01, relaunchIfRunning=false).
    OK   connected
    OK   appConnected E1C0DE01 launched=true session=b67d9688-1469-4fab-94b6-72ad909b848e
    OK   connected
    OK   appConnected E1C0DE01 launched=false session=b67d9688-1469-4fab-94b6-72ad909b848e
    ALL OK
- The receiver saw 1 LAUNCH in total, from session A only. Session B joined A's session.
- On W03's delivered code (0002 = b64f81ed), the same driver exited 1: B sent a second LAUNCH and got a new session.

## Not covered by this run
- No real Chromecast.
- The binder layer (CastDeviceControllerImpl, the service) is not exercised on the host; only the channel and session classes are.
