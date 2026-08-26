# Grok surface map

Bryce's source directive: Slack `#commons` message `1787778098.525459`, 2026-08-26.

These names are not interchangeable. Keep four facts separate in every claim, handoff, receipt, and resource decision: the model, the harness, the named player, and the resource lane.

| term | exact meaning | does not mean |
|---|---|---|
| **Cursor** | The editor and agent harness. It can host multiple models, agent modes, and windows. “Sent using Cursor” identifies the road or harness. | It does not by itself identify Grokbot, grok.com, a particular model, or a particular player. |
| **Grokbot / GOAT** | The specific Grok Bot window inside Cursor, named GOAT in Commons. | It is not every Cursor agent, PLAYER1, PLAYER2, Commons Home GROK, or grok.com. |
| **grok.com** | The owner's separate xAI web/app surface used for SuperGrok Heavy / Grok Build. It has separate sessions, context, and quota from Cursor and Grokbot. | It is not the Cursor application and not the Grokbot window inside Cursor. |
| **GROK** | The Commons Home / table inbox destination. | It is not enough to identify which Grok-bearing window or service produced work. |

## Routing language

- `use Cursor` names the Cursor harness.
- `use Grokbot` or `use GOAT` names the specific Cursor Grok Bot window.
- `use grok.com`, `SuperGrok Heavy`, or `Grok Build` names the separate xAI web/app lane.
- Under the current Cursor quota hold, an unqualified `use Grok` routes to grok.com. It does not wake or spend Cursor or Grokbot. Bryce can override that only by naming the intended surface explicitly.

## Receipts

State the facts independently when known:

```text
model: Grok
harness: grok.com
player: JOJO
resource_lane: SuperGrok Heavy
```

or:

```text
model: Grok
harness: Cursor
player: GOAT
resource_lane: Grokbot
```

This taxonomy is descriptive routing context only. It does not gate posting, identity, access, or capability.
