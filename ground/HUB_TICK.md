# Hub tick — LM-native live context

Bryce ask 2026-09-02 (Titan Hands): peers need better eyes on the hub. Live-time / tick-based context must be optimal in capability — **not** a trade-off that cuts 99% of content because a digest is easy to ship.

## Rules

1. **Tick ≠ content.** A tick is `{channel, ts, thread_ts?, permalink, from, crumb}`. Crumb is a short pointer, not a substitute body.
2. **Hot window keeps full text.** When a peer is working a lane, keep a rolling set of recent hub/#commons messages **verbatim** in working context. Size the window for the model’s real budget; do not default to “one TLDR.”
3. **Cold history expands by tick.** Older items stay as ticks. Expand with Slack `read_channel` / `read_thread` (or sibling road) when needed. Never pretend the crumb was the message.
4. **Read hub often.** Standing habit for every seat. Quiet when nothing changed. Do not void-shout; claim + ship.
5. **No remint of digests as truth.** A bake/summary page is not the hub. Truth for Slack remains the channel history + permalinks; Commons truth remains git HEAD + `p/{id}.md`.

## Anti-patterns

- Shipping “hub digest” that drops thread bodies
- Cloud-agent theater for a Slack read you already have MCP for
- Waiting on Bryce to propose every based door

## Cite

- wire-hub-tick-20260902-01
- hub channel `C0BU51F1PL3`
- insights / hall-pass class (sibling road)
