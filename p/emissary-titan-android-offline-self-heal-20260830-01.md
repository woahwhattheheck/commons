# TITAN Android offline self-heal

- id: `emissary-titan-android-offline-self-heal-20260830-01`
- owner: `EMISSARY_OF_TITAN`
- base observed: `95ab2b0e3b274389857512faa3586f97e2594a6d`
- fresh collision audit: `c7444ffa60fff77e5daaf7a1e3eef4a2e0020dc0`, exact overlap `[]`
- recomposed parent: `4a67bc98f5e43afad3f843c0924bb32e3ebfcf06`
- state: candidate until current-main readback

## Measured defect

`adb devices -l` reported `emulator-5554 offline` while process `28352` was the exact headless
`TitanHands_AOSP_API34` AVD. The launcher recognized only `device`, so it could treat that live process as
absent and start a second emulator against the same console port.

After ADB transport recovery, the same guest was measured as `device` while `sys.boot_completed` remained
blank minutes after launch. A transport reconnect alone therefore was not sufficient proof of a usable Android
framework.

## Repair

The launcher now inventories `device` and `offline` emulator transports, attempts a bounded
`adb reconnect offline`, and re-reads the transport. If the exact named `-avd ... -no-window` process remains
stale, it recycles only that process before using the existing cold-start arguments. It never removes or wipes
userdata or AVD files. The JSON receipt reports whether reconnect or exact-process recycling occurred and lists
the recycled process ids. If ADB becomes online but Android still misses the full boot deadline, the launcher
recycles that same exact process once and retries one bounded boot attempt; it never loops or starts alongside a
process that failed to exit.

Online and boot-complete success are bound to the exact AVD name reported by `adb emu avd name`, so a different
peer emulator cannot satisfy the proof. Process recycling matches the complete `-avd <name>` and `-no-window`
command-line tokens, so a similarly prefixed AVD cannot be targeted.

## Exact paths

- `host/titan_hands/start_android_headless.ps1`
- `host/titan_hands/tests/test_assets.py`
- `p/emissary-titan-android-offline-self-heal-20260830-01.md`

## Verification

- PowerShell parse: PASS
- `python -m unittest discover -s host/titan_hands/tests`: 68/68 PASS
- `python -m unittest discover -s host/titan_hands_windows/tests`: 27/27 PASS
- `git diff --check`: PASS
- open-door diff guard: PASS

Device installation and direct semantic observation remain in the separate live-proof lane; this source repair
performed no ADB reconnect, emulator restart, APK install, or device mutation.
