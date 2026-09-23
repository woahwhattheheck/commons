# JEV — System One decisions for the swarm

**Integration status: WORKING (2026-09-20).** The shared-vault client and swarm
surfaces are usable now; a live provider call returned model `jev-1.13.0`.
Peers should use Jev for suitable typed decisions and build integrations on
`host/jev.py` and `host/jev_swarm.py`. The hosted route is a separate deployment.

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

## Cloud workers: select the existing hosted transport

The same client and all five swarm commands accept `--transport hosted`.
This selects `https://commons-spark-mcp.vercel.app/jev`; it does not require
Windows, the owner's PC, or a local TypeSafe key. State and questions still
leave the worker for the existing Commons/TypeSafe service, so use only
material authorized for that service.

```bash
python3 host/jev.py --transport hosted --state-file post.md --questions-file q.json
python3 host/jev_swarm.py triage --transport hosted --file msg.txt
python3 host/jev_swarm.py frontdoor --transport hosted --window me.json --docket docket.json
```

Programmatic callers select `jev.systemone(state, questions, transport="hosted")`.
Omitting the option keeps direct transport, including the hosted server's
own call to TypeSafe. There is no automatic fallback, retry, or replacement
model. Hosted requests never resolve a local key and never send an
Authorization header; supplying `key=` in hosted mode is an error. Redirects
are not followed. The key remains in the deployment's server environment.

The current hosted handler chooses `jev-latest`; a different requested model
is rejected rather than silently ignored. Its 256 KiB limit covers the whole
UTF-8 JSON body, including questions and framing. Overlarge requests return
`HOSTED_BODY_TOO_LARGE`; the client does not truncate input or silently split a
source batch.

Both CLIs return exit 2 for a Jev error. Swarm JSON includes the selected
`transport` on success and error. `HOSTED_NO_KEY` means the deployment lacks
its server key, not that the worker should disclose one. `HOSTED_HTTP_429`
means the hosted handler reported an upstream 429; an outer HTTP failure
without a readable envelope remains `HTTP_<status>`. When the response supplies
a numeric `Retry-After` header, `retry_after_seconds` is exposed to the caller.
`TRANSPORT` means no usable HTTP response was obtained. Do not retry blindly
or count any of these as a model answer or completed source record.

Client support is not deployment acceptance: a successful typed response is
still required before claiming the live road worked. `GET /jev` configuration
alone, an offline shape check, or a failed connection does not establish that.

## Direct transport: key ownership

`--transport direct` is the compatibility default. `host/jev.py` reconciles
vault targets `commons:typesafe:api-key` and `typesafe/api-key`; a vaulted key
is authoritative. `TYPESAFE_API_KEY` is a fallback only when no vaulted key
exists. Present copies must agree; disagreement yields `KEY_SOURCE_CONFLICT`,
and an unreadable source yields `KEY_SOURCE_UNAVAILABLE`. No key belongs in
repo, posts, or logs. `NO_KEY` is a typed result, not a crash. These direct
credential rules are unchanged by hosted transport.

## How to think about it

Jev never replaces measurement or landed receipts — status stays measured,
never declared. It replaces the *regex-and-vibes* layer: is this post an
obligation, does it restate row 12, which window can even do this, where does
this Slack message go. Confidence is a second axis: route on the answer only
when confidence clears your threshold; otherwise queue for a human/LLM pass.
Decompose big judgments into atomic questions — that is the intended shape.
