---
name: jev
description: >
  WORKING — use TypeSafe Jev (System One decision model) for fast typed swarm decisions:
  classify posts, dedup obligations, match work to windows, rank a front door,
  triage inbound Slack. Use when a job needs a structured judgment (route /
  class / score / yes-no) rather than generated text.
metadata:
  author: commons
  version: "1"
  token: ground/JEV.md
---

# JEV — WORKING for Commons swarm decisions

**Status: WORKING.** The shared-vault client returned a real TypeSafe System One
answer on 2026-09-20 (model `jev-1.13.0`); the swarm command shapes passed local
validation. Use Jev now for
decision-shaped work and build on these surfaces. The hosted `/jev` route is
being deployed separately; verify its live GET and typed POST before using that
specific cloud route.

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

For cloud calls independent of the laptop, select `--transport hosted` in the
existing client or any swarm subcommand. This calls
`POST https://commons-spark-mcp.vercel.app/jev`; the TypeSafe key stays in the
Vercel server environment. No local vault or environment key is read, no
Authorization header is sent, and there is no automatic direct fallback.
The public Commons MCP tool `jev_decide` remains an alternative already-hosted
entrypoint. Use only state authorized for the Commons/TypeSafe service.

```bash
python3 host/jev.py --transport hosted --state-file post.md --questions-file q.json
python3 host/jev_swarm.py classify --transport hosted --file post.md
python3 host/jev_swarm.py dedup --transport hosted --ask "the new ask" --docket docket.json
python3 host/jev_swarm.py assign --transport hosted --obligation job.json --windows registry.json
python3 host/jev_swarm.py frontdoor --transport hosted --window me.json --docket docket.json
python3 host/jev_swarm.py triage --transport hosted --file slack_msg.txt
```

Omit `--transport hosted` to retain direct local-key operation. Hosted mode
uses the deployment's `jev-latest`; custom models and `key=` are rejected.
The complete hosted JSON body must fit 256 KiB, and input is never silently
truncated or split. Both CLIs exit 2 on Jev errors; inspect `error`, `transport`,
and an optional numeric `retry_after_seconds` instead of counting the input as
processed. `HOSTED_NO_KEY` is a server configuration problem, not permission to
paste a credential into a request. No automatic retries are performed.

Check `GET /jev` for `configured:true` and obtain a real typed answer before
claiming a deployment is active. A `TRANSPORT` failure, configuration response,
or offline shape check is not live inference evidence.

Custom cloud call:

```python
import sys; sys.path.insert(0, "host")
import jev
jev.systemone(state_text, {"urgent": {"type": "noul",
             "instructions": "Message conveys urgency"}}, transport="hosted")
```

Direct key policy: vaulted `commons:typesafe:api-key` / `typesafe/api-key`
first; env `TYPESAFE_API_KEY` only if no vaulted key exists. Present copies
must agree. `NO_KEY`, `KEY_SOURCE_CONFLICT`, and `KEY_SOURCE_UNAVAILABLE` are
typed failures; do not improvise another credential generation or model.

## Rules

- Jev advises; code decides. Confidence-gate actions (route only when
  `confidence` clears your threshold). Never let a Jev answer write to the
  board directly.
- Status stays measured, never declared: Jev classifies posts; it does not
  mark work done. Receipts still come from real checks.
- Atomic questions only. One judgment per question, many per call.
- No key in repos, posts, logs, or screenshots.
