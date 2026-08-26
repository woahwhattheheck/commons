# TITAN Hands — direct local semantic computer use

This broker exposes one MCP surface for two deterministic hands:

- `target=windows`: Microsoft UI Automation, UIA control patterns, and native input fallback.
- `target=android`: ADB + UIAutomator XML, with the same semantic delta contract.

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

The Android adapter supports click/invoke/focus/toggle, text entry, key events, scrolls, package launch,
wait, and explicit PNG capture. It never requires a physical handset: a headless AVD is the intended
default colony target.

On a fresh Windows host, install the user-local SDK/AVD and boot it without a display:

```powershell
powershell -File host/titan_hands/setup_android_headless.ps1 -AcceptSdkLicenses
powershell -File host/titan_hands/start_android_headless.ps1
```

The setup script verifies the official command-line-tools SHA-256, installs only the command-line SDK,
emulator, API 34 platform, and lightweight x86_64 AOSP image, and stores them under LocalAppData. With
`TITAN_HANDS_ANDROID_AUTOSTART=1`, the broker starts that AVD automatically on the first Android action or
observation when no target is online.

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
