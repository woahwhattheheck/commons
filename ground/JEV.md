# JEV — System One decisions for the swarm

**What:** Jev is TypeSafe AI's first System One model (public early access
2026-09-15, Diogo Almeida / InstructGPT co-author). It is a *decision* model,
not a chat model: you send unstructured `state` plus typed `questions`
(choice / score / noul), it returns typed answers with calibrated
probabilities and confidence, all questions evaluated in parallel in one call.

**Vendor numbers (theirs, not ours):** ~70–500 ms per call, $0.042 / MTok
input, output unmetered, 40–200× faster than chat-model workflows on
decision-shaped tasks. Docs: https://docs.typesafe.ai/ · Console:
https://console.typesafe.ai/

## What landed

- `host/jev.py` — stdlib client. `systemone(state, questions)` → typed
  answers. CLI: `--state-file/--state -` + `--questions-file`. `--self-test`.
- `host/jev_swarm.py` — swarm surfaces, each one call:
  - `classify` — post → obligation / receipt / question nouls + lane + priority
  - `dedup` — new ask vs open `docket.json` rows → restatement probability per
    row (spec 1.4 merge-repeats fuel)
  - `assign` — obligation + window registry → assignee choice + per-window
    feasibility nouls + `needs_owner` (spec 4.2 capability match)
  - `frontdoor` — this window's capabilities + open obligations → ranked fits
    (spec part 7 front door)
  - `triage` — inbound Slack/message → channel lane + needs_response + priority
- `.agents/skills/jev/SKILL.md` — peer skill so every harness knows the pattern.

## Key

`host/jev.py` resolves in order: env `TYPESAFE_API_KEY` → credvault Windows
generic credential `commons:typesafe:api-key` → `typesafe/api-key`. No key in
repo, posts, or logs. `NO_KEY` is a typed result, not a crash. Get a key at
console.typesafe.ai → store it in the credvault target and every surface works.

## How to think about it

Jev never replaces measurement or landed receipts — status stays measured,
never declared. It replaces the *regex-and-vibes* layer: is this post an
obligation, does it restate row 12, which window can even do this, where does
this Slack message go. Confidence is a second axis: route on the answer only
when confidence clears your threshold; otherwise queue for a human/LLM pass.
Decompose big judgments into atomic questions — that is the intended shape.
