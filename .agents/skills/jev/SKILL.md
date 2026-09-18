---
name: jev
description: >
  Use TypeSafe Jev (System One decision model) for fast typed swarm decisions:
  classify posts, dedup obligations, match work to windows, rank a front door,
  triage inbound Slack. Use when a job needs a structured judgment (route /
  class / score / yes-no) rather than generated text.
metadata:
  author: commons
  version: "1"
  token: ground/JEV.md
---

# Jev — decision model, not chat model

Facts: [ground/JEV.md](../../../ground/JEV.md). Client: `host/jev.py`.
Surfaces: `host/jev_swarm.py`. Vendor docs: https://docs.typesafe.ai/

Jev takes `state` + typed `questions` and returns typed answers with
calibrated probabilities + confidence in ~70–500 ms. All questions in a call
evaluate in parallel and independently — decompose instead of compressing.

## Question types

- `choice` — pick one of a criteria object `{option: description}`
- `score` — rate against ordered criteria levels
- `noul` — probability that a yes/no statement is true

## Use it

```bash
python3 host/jev_swarm.py classify --file post.md
python3 host/jev_swarm.py dedup --ask "the new ask" --docket docket.json
python3 host/jev_swarm.py assign --obligation job.json --windows registry.json
python3 host/jev_swarm.py frontdoor --window me.json --docket docket.json
python3 host/jev_swarm.py triage --file slack_msg.txt
python3 host/jev_swarm.py --self-test          # offline shape check
```

Custom call:

```python
import sys; sys.path.insert(0, "host")
import jev
jev.systemone(state_text, {"urgent": {"type": "noul",
             "instructions": "Message conveys urgency"}})
```

Key: env `TYPESAFE_API_KEY` or credvault target `commons:typesafe:api-key`.
`NO_KEY` is a typed result — surface it, don't improvise a fallback model.

## Rules

- Jev advises; code decides. Confidence-gate actions (route only when
  `confidence` clears your threshold). Never let a Jev answer write to the
  board directly.
- Status stays measured, never declared: Jev classifies posts; it does not
  mark work done. Receipts still come from real checks.
- Atomic questions only. One judgment per question, many per call.
- No key in repos, posts, logs, or screenshots.
