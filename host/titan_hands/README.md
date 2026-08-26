# TITAN Hands — direct local semantic computer use

This broker exposes one MCP surface for two deterministic hands:

- `target=windows`: Microsoft UI Automation, UIA control patterns, and native input fallback.
- `target=android`: the owner's LDA Kotlin translation layer over ADB, with UIAutomator only as a
  compatibility fallback when the LDA APK/accessibility service is absent.

The ordinary loop transfers no screenshots. Both adapters emit stable semantic nodes and compact
added/updated/removed deltas; pixels move only through `hands_capture`. The server itself contains no
confirmation or approval dialogue.

## Run

From the Commons repository root:

```powershell
python -m host.titan_hands.mcp_server
```

The MCP tools are:

- `hands_targets`
- `hands_capabilities`
- `hands_observe`
- `hands_act`
- `hands_capture`

Every tool except `hands_targets` and an untargeted capability catalog accepts `target=windows|android`.
Windows is the default.

## Android target selection

TITAN selects an emulator by default and never silently falls through to a plugged-in physical handset. To
use a purchased colony phone later, set `TITAN_HANDS_ANDROID_SERIAL` to its exact ADB serial. A missing
emulator returns `DEVICE_MISS`; it does not make the Windows hand unavailable.

When LDA is installed, normal perception is the exact compact numbered world-model produced by
`ActionAccessibilityService.snapshotScreen()`, and actions execute through the existing
`performActionJson()` Kotlin implementation. That preserves the owner's element paging, target retargeting,
Set-of-Marks representation, action salvage, verification, gesture fallbacks, and learned actuator policy.
TITAN adds transport and the cross-platform MCP surface; it does not replace the handset operator.

The LDA action language remains free-form and reachable through `hands_act`. Common TITAN verbs are translated
to the native equivalents (`type_text` becomes `set_text`, `launch` becomes `open_app`); native LDA verbs such as
`find`, `aim`, `tap_grid`, `draw`, `sketch`, `assert`, and `get_text` pass through unchanged.

On a fresh Windows host, install the user-local SDK/AVD and boot it without a display:

```powershell
powershell -File host/titan_hands/setup_android_headless.ps1 -AcceptSdkLicenses
powershell -File host/titan_hands/start_android_headless.ps1
powershell -File host/titan_hands/install_lda_emulator.ps1
```

The setup script verifies the official command-line-tools SHA-256, installs only the command-line SDK,
emulator, API 34 platform, and lightweight x86_64 AOSP image, and stores them under LocalAppData. With
`TITAN_HANDS_ANDROID_AUTOSTART=1`, the broker starts that AVD automatically on the first Android action or
observation when no target is online.

`install_lda_emulator.ps1` builds the repository's real `lda/` Kotlin application, installs it into the
headless emulator, enables its existing accessibility service, and probes `TitanHandsReceiver`. It refuses a
physical handset unless both an explicit serial and `-AllowPhysicalDevice` are provided.

The inventoried source-version gaps have been repaired from the owner's real LocalDeviceAgent tree. The
x86_64 headless build, APK install, strict accessibility-ready probe, native Kotlin observation, native click,
and changed post-action semantic digest are live-proven. `auto` still keeps UIAutomator as an honest fallback
when the LDA APK/service is absent; it reports `lda-kotlin` only when that service is actually ready. Exact
inheritance and proof details are in [GROK_HANDOFF.md](./GROK_HANDOFF.md).

## Codex registration

Codex local clients share MCP configuration. Register this module as a STDIO server with the repository
root as `cwd`, then set `default_tools_approval_mode = "approve"` for the `titan_hands` server. New Codex
sessions will receive the five tools directly; an already-running task retains its original tool inventory.

Official configuration reference: <https://developers.openai.com/codex/mcp/>

For a reproducible global registration using Codex's no-prompt `approve` mode:

```powershell
powershell -File host/titan_hands/register_codex.ps1
```

The ChatGPT desktop app, Codex CLI, and IDE extension share that MCP configuration. Restart the local client
or begin a new task after registration; an already-running task cannot gain a new tool inventory mid-turn.

Architecture and the exact headless boundary: [ARCHITECTURE.md](./ARCHITECTURE.md).
Owner-source inheritance and the Grok continuation map: [GROK_HANDOFF.md](./GROK_HANDOFF.md).
