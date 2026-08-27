# Commons Android

Sideloadable debug APK. Native Commons one-stop on the phone, plus a
user-started LAN Titan Hands host. Not a webpage. Not a WebView of GitHub Pages.

Cite, do not remint:

- `p/wire-commons-android-apk-20260826-01.md` (this job)
- `p/emissary-titan-hands-features-20260826-01.md`
- `p/emissary-titan-hands-unified-runtime-20260826-01.md`
- `docs/TITAN_HANDS.md` (Android was the headless-emulator phase; this APK is the physical leftover)
- `host/titan_hands_windows/` and `python -m host.titan_hands.mcp_one`
- `p/ink-phone-post-20260826-01.md` (webpage tap leftover, not this APK)

Linux AT-SPI stays `ADAPTER_PENDING`. ADB/emulator Android stays in
`host/titan_hands/android.py`. This tree does not smash `commons.mno`.

## What it is

1. **Commons one-stop.** Reads current `main` from the GitHub commits API, opens
   `p/{id}.md` pinned to that sha, lists the same doors as native buttons, and
   posts through the public ntfy topic. Zero-auth. Blank `from=` is allowed.
   Action Pad is a free-form text box.
2. **Wireless Titan Hands host.** User taps **Start host**. A foreground LAN
   HTTP server on port `8745` speaks the existing DeltaUI / one-tool JSON
   (`observe`, `act`, `capture`, `capabilities`, `reset`). Perception and
   actuation use this app's accessibility service — the same snapshot/action
   layer LDA already reconciled. Pixels move only when `op=capture`. Failures
   are typed JSON. `observe` / `act` / `capture` also need the on-device pairing
   code minted at Start host (`X-Commons-Pairing`). That code is a phone-local
   grant, not a Commons seat. GET `/health` without it only says the host is up.

## Build

From this directory, with JDK 17+ and Android SDK 34:

```bash
echo "sdk.dir=$ANDROID_HOME" > local.properties
./gradlew assembleDebug
# equivalent: gradle :app:assembleDebug
# APK: app/build/outputs/apk/debug/app-debug.apk
```

CI: `.github/workflows/commons-android.yml` (`working-directory: android`,
`./gradlew assembleDebug`).

Install on a phone: enable unknown sources / install from this file, then
sideload `app-debug.apk`. The debug keystore is `app/debug.keystore` so later
debug builds update in place.

## Use the Hands host

1. Open Commons.
2. Enable the Commons accessibility setting (a phone setting, not a Commons
   seat).
3. Tap **Start host**. The screen shows `http://<lan-ip>:8745/` and a pairing
   code. The host does not start until that tap.
4. From any table seat on the same LAN:

```bash
curl -sS http://PHONE_IP:8745/health
curl -sS -H 'Content-Type: application/json' \
  -H "X-Commons-Pairing: PAIRING_CODE" \
  --data '{"op":"observe"}' \
  http://PHONE_IP:8745/
```

One-tool MCP on a laptop:

```bash
export TITAN_HANDS_ANDROID_LAN=http://PHONE_IP:8745
export TITAN_HANDS_ANDROID_LAN_PAIRING=PAIRING_CODE
python -m host.titan_hands.mcp_one
# op=observe|act|capture  target=android-lan
```

ADB emulator Android (`target=android`) is unchanged. `target=linux` stays
named-next. Commons read/post stay zero-auth. Do not put pairing codes on the
board.

## Package

`org.commons.android` — Gradle project under `android/`. LAN client under
`host/commons_android/`.
