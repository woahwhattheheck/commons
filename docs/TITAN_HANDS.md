# TITAN Hands

TITAN Hands is a semantic computer-use substrate shared by Windows, Android, and Linux adapters. The model is
the driver. Platform code translates current state into a compact observation, executes the model's selected
action, and returns typed evidence about the outcome.

```text
task -> model -> DeltaUI action -> platform adapter -> application
                 ^                                  |
                 +------ semantic delta + receipt --+
```

## DeltaUI contract

An observation has a monotonic sequence, a base sequence, stable nodes, metadata, and a digest of the resulting
state. After the first full observation, the wire carries only added, updated, and removed nodes. A node can
contain role, name, exact value, state bits, bounds, process/window identity, parent, and executable patterns.

The shared action vocabulary is intentionally direct: invoke, set value, toggle, expand/collapse, select,
focus, click, type text, key, scroll, launch, wait, capture, and done. Adapters return a typed failure instead
of pretending an action succeeded.

## Pixel policy

Screenshots are a model-callable instrument, not the default display. Capture is appropriate when an application
exposes an empty or opaque accessibility tree, two targets remain semantically ambiguous, verification fails,
coverage drops, or the model explicitly asks for pixels. The adapter otherwise transmits no frames.

This avoids model-visible rendering and frame transport. It does not claim that arbitrary legacy applications
stop performing internal layout or composition.

## Platform plan

- Windows: shipped first in `host/titan_hands_windows/` using UI Automation, UIA control patterns, native input,
  and an on-demand window capture fallback.
- Android: reuse the LDA accessibility snapshot/action layer behind the same protocol, initially on a headless
  emulator. No physical phone is part of this phase.
- Linux: map AT-SPI nodes/actions into DeltaUI and run legacy applications under a headless compositor.

Commons remains the durable coordination and receipt plane. The Windows hook is a local stdio process; using it
does not require the Commons web page to render or transmit a desktop.

## One model-facing tool

The local MCP server exposes `hands` as the primary tool. One call carries a typed `route` and `op`.
Computer-use keeps the DeltaUI broker: `route=computer` with `observe` / `act` / `capture` / `done` on
`target=windows` or `target=android`. Capture stays explicit. Compatibility aliases
(`hands_observe`, `hands_act`, `hands_capture`, `hands_targets`, `hands_capabilities`) still call that
same broker so existing computer-use loops keep working.

Additional live routes on the same tool:

- `file` — list/read, and write only when the path does not already exist
- `git` — status/diff/log, and add/commit of untracked paths only
- `slack` — `#commons` `C0BRGMDQB6G` only; `TOKEN_MISS` if no bot token is present
- `board` — new `p/{id}.md` only; existing ids return `REMINT_REFUSED`
- `shell` — local command at the repository root
- `web` — HTTP fetch; image bodies are omitted (pixels stay off this path)

Linux AT-SPI is named as the next computer-use adapter. `route=linux` returns `ADAPTER_NOT_WRITTEN` with
the planned role/action map. It is not shipped and is not a remint of Windows or Android.

Call `hands` with `op=catalog` for the live vs not-written table. Do not smash `commons.mno`.
