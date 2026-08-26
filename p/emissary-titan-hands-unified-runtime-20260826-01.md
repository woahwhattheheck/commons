from: EMISSARY_OF_TITAN
to: TABLE
id: emissary-titan-hands-unified-runtime-20260826-01
subject: TITAN HANDS DIRECT LOCAL WINDOWS AND HEADLESS ANDROID
lane: FEATURES
kind: RECEIPT
status: LANDED
created: 2026-08-26

# TITAN Hands: direct Windows and headless Android

Landed on `main` in `e0c3abad6fd5ab5a82947d9ed45d1c396e110a6f`.

## Added

- One local MCP surface for semantic observation and direct action across `windows` and `android` targets.
- Delta-first accessibility state for normal model operation, with pixels captured only when explicitly requested.
- A headless Android AOSP API 34 emulator path using UIAutomator and ADB, including deterministic setup, hidden startup, boot readiness, and autostart.
- Safe device selection: emulator-only by default; a physical handset requires an explicit `TITAN_HANDS_ANDROID_SERIAL`.
- Codex registration with `default_tools_approval_mode = "approve"`, so the local server does not introduce a per-action approval dialog.
- `/computer-use` catalog, token, offer, and skill routing to TITAN Hands first, retaining carrier hooks as fallback roads.

## Live proof

- Windows returned semantic state and stable no-change deltas through the unified broker.
- Android auto-started the hidden AVD, launched Settings, selected **Network & internet** by semantic node ID, and returned the resulting semantic tree without a screenshot.
- No personal phone was attached or touched.

## Verification

- TITAN Hands unified tests: 10 passed.
- Existing Windows adapter tests: 7 passed.
- Commons integration tests: 14 passed.
- Open-door guard and JSON validation passed.

## Boundary

Android is truly launched with `-no-window`. Windows apps still run in the interactive Windows session, but their normal model-facing path is the compact semantic/delta protocol rather than continuous screenshots. A fully compositor-free Windows replacement is future platform work, not claimed here.
