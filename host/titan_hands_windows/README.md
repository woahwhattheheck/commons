# TITAN Hands — Windows adapter

This is the local Windows hand for Commons. It observes applications through Microsoft UI Automation,
returns deterministic semantic deltas, actuates UIA control patterns first, and uses native input only when
an application does not expose a semantic pattern. Pixels are absent from ordinary observations and are
captured only through an explicit `capture` request.

## Run

From the Commons repository root:

```powershell
python -m host.titan_hands_windows.server --request '{"op":"capabilities"}'
python -m host.titan_hands_windows.server --request '{"op":"observe","max_nodes":300}'
python -m host.titan_hands_windows.server
python -m host.titan_hands_windows.mcp_server
```

The plain server and MCP facade both use newline-delimited JSON on stdio. The PowerShell backend stays alive
behind the Python process so node IDs refer to cached `AutomationElement` objects between observation and actuation.

## Wire examples

```json
{"op":"observe","max_nodes":600,"max_depth":8}
{"op":"act","action":{"type":"invoke","id":"w_0123456789abcdef0123"}}
{"op":"act","action":{"type":"set_value","id":"w_0123456789abcdef0123","value":"hello"}}
{"op":"act","action":{"type":"key","key":"ctrl+l"}}
{"op":"capture","id":"w_0123456789abcdef0123","path":"artifacts/titan-hands/window.png"}
```

Every successful action observes again by default and returns the resulting semantic delta. Failures use stable
classes such as `ELEMENT_STALE`, `PATTERN_UNAVAILABLE`, `WINDOW_MISS`, `ACTION_FAILED`, and `CAPTURE_FAILED`.

## Current pixel fallback

The first backend attempts `PrintWindow`, which can capture many occluded desktop windows, and falls back to
`CopyFromScreen`. A future adapter may replace this implementation with `Windows.Graphics.Capture` without
changing the model-facing protocol.
