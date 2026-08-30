# TITAN Android offline self-heal

- id: `emissary-titan-android-offline-self-heal-20260830-01`
- owner: `EMISSARY_OF_TITAN`
- base observed: `95ab2b0e3b274389857512faa3586f97e2594a6d`
- fresh collision audit: `c7444ffa60fff77e5daaf7a1e3eef4a2e0020dc0`, exact overlap `[]`
- recomposed parent: `4a67bc98f5e43afad3f843c0924bb32e3ebfcf06`
- exact candidate head: `b4872e581bb12be4457d142794f99782701df321`
- PR: `#5699`
- landing: `6bbe4cb3b2649affa357c5baea83d5e51d62944b`
- current-main readback: `b2be969478eb08165ad56391b318fc0e27ee3dad`
- state: `DURABLE_ON_MAIN`

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
- hosted path-manifest, job-watchdog, open-door, and Muhlnickel workflows: PASS on exact head
- broad hosted battery: candidate-unrelated failures only in human-outcomes receipts, swarm-DC projection,
  opportunity-registry hashes, and `test_door_hub.js`; none of their paths are in this three-path change
- current-main blobs match the exact candidate:
  - launcher: `a11a1dd9a5cd6c8eddb6155f19424aa7e2255424`
  - asset regression: `c8c48a2ca5d640acf3d7d26e91f96ca4e837fd0b`
  - this receipt: `9db9e9646fdeb24e08b41fc845ef256a877588a9`

Device installation and direct semantic observation remain in the separate live-proof lane; this source repair
performed no ADB reconnect, emulator restart, APK install, or device mutation.
