# ASTER BRIDGE — connection guide

A local, authenticated adapter that exposes **capabilities** and nothing else.

This document has two parts.

| Part | Audience | Shareable? |
|---|---|---|
| **Part 1 — the interface** | Aster | Yes. Contains no host detail. |
| **Part 2 — host operation** | The owner only | **No.** Contains local locations and the token procedure. |

---
---

# PART 1 — THE INTERFACE  *(safe to hand to Aster)*

## What this is

A single loopback endpoint offering **13 capability operations**. Every reply is
built from a declared contract. Identifiers are opaque: they are stable, they
are usable as inputs to later calls, and they carry no meaning outside the
bridge.

## What this deliberately is not

The bridge exposes capability **verbs and results**. It does not expose the
things that produce them — no source, no configuration, no internal names, no
locations, no diagnostic text. This is enforced in code, not by convention:

- an operation absent from the manifest is **refused**;
- every emitted field is re-proven against a declared contract, and a field
  that cannot be proven **fails the call instead of crossing**;
- errors are constant codes — an internal fault yields `E_INTERNAL` and a
  fixed sentence, never the underlying detail;
- identifiers are opaque handles minted from a host-only secret.

If a request errors where you expected data, the boundary did its job. Retry
with different inputs; the refusal is not negotiable from the client side.

## Transport

```
POST http://127.0.0.1:7891/rpc
Authorization: Bearer <token issued by the host>
Content-Type: application/json

{ "verb": "<operation>", "params": { ... } }
```

Also available to an authenticated caller:

```
GET http://127.0.0.1:7891/manifest    -> the machine-readable schema
GET http://127.0.0.1:7891/health      -> liveness only
```

**Every** route demands the bearer token. There is no anonymous surface.

## Envelope

Success:
```json
{ "ok": true,  "verb": "status", "ts": "2026-08-05T00:37:20Z", "data": { ... } }
```
Failure:
```json
{ "ok": false, "verb": "status", "ts": "2026-08-05T00:37:21Z",
  "error": { "code": "E_INTERNAL", "message": "request could not be completed" } }
```

`verb` is echoed **only** when it names a real operation; otherwise it is
`null`. Client-supplied text is never reflected back.

## Error codes

| Code | Meaning |
|---|---|
| `E_AUTH` | authentication required |
| `E_METHOD` | unsupported request |
| `E_VERB` | unknown operation |
| `E_PARAM` | invalid parameters |
| `E_CONTENT` | content refused by policy (inbound) |
| `E_SANITIZE` | result withheld by policy (outbound) |
| `E_STATE` | resource not available |
| `E_LIMIT` | too many requests |
| `E_INTERNAL` | request could not be completed |

`E_CONTENT` means the text you sent contained protected vocabulary and was
refused **on the way in**, so it can never be stored and read back later.

## Operations

| Verb | Params | Returns |
|---|---|---|
| `status` | — | `live`, `generation`, `utilization_band`, `workload_count`, `uptime_band`, `surface_ok`, `participant_count` |
| `players.list` | — | `players[]` of `handle`, `label`, `role`, `state`, `last_seen_band`; `count` |
| `players.message` | `to` (handle or `*`), `body` | `delivered`, `receipt`, `ts` |
| `surface.state` | — | `width`, `height`, `depth`, `cell_count`, `generation`, `consistent`, `last_settled` |
| `home.read` | `limit` | `entries[]`, `count`, `total` |
| `home.write` | `text` | `id`, `ts`, `total` |
| `scratch.read` | `limit` | `entries[]`, `count`, `total` |
| `scratch.write` | `text` | `id`, `ts`, `total` |
| `task.submit` | `objective`, `detail` | `task`, `state`, `ts` |
| `task.observe` | `task` | `task`, `state`, `progress_band`, `steps_done`, `note`, `ts` |
| `optimize.list` | — | `capabilities[]` of `handle`, `objectives[]`, `state`; `count` |
| `optimize.request` | `capability`, `objective`, `bound` | `receipt`, `capability`, `objective`, `accepted`, `generation`, `ts` |
| `receipt.get` | `receipt` | `receipt`, `ts`, `verb`, `outcome`, `generation` |

`home.*` is durable across restarts. `scratch.*` is emptied on every restart.

Optimization is addressed **only** by the opaque handle from `optimize.list`.
There is no name-based form of the call, and the objective must be one the
capability advertises or the request is refused with `E_STATE`.
`optimize.request` returns a **receipt of acceptance**; poll `receipt.get` for
the outcome and the configuration-generation identifier.

Every operation also accepts three optional diagnostic flags —
`probe_fault`, `probe_taint`, `probe_undeclared`. Each one deterministically
produces a redacted error (`E_INTERNAL`, `E_SANITIZE`, `E_SANITIZE`). They
exist so the boundary can be verified from the outside rather than taken on
trust. They never return data.

## Worked example

```bash
curl -s http://127.0.0.1:7891/rpc \
  -H "Authorization: Bearer $ASTER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"verb":"optimize.list","params":{}}'
```
```json
{"ok":true,"verb":"optimize.list","ts":"2026-08-05T00:37:21Z",
 "data":{"capabilities":[
   {"handle":"cap_4be7c16a003b5c63","objectives":["throughput","latency"],"state":"available"}],
  "count":5}}
```
```bash
curl -s http://127.0.0.1:7891/rpc \
  -H "Authorization: Bearer $ASTER_TOKEN" -H "Content-Type: application/json" \
  -d '{"verb":"optimize.request","params":{"capability":"cap_4be7c16a003b5c63","objective":"throughput"}}'
```

---
---

# PART 2 — HOST OPERATION  *(owner only — do not share)*

## Launch

```
cd C:\Users\lucys\Desktop\MUHLNICKEL_LOOM\bridge
python aster_bridge.py --port 7891
```

Refuses to start unless the bind address is `127.0.0.1`, the deny-list loaded,
and the port is outside the reserved set `{7881, 7882, 7883, 7890, 7899}`.

Regenerate the published schemas after any change to the allowlist:

```
python aster_bridge.py --emit-manifest --emit-openai
python test_leakage.py
```

## Files

| File | Role |
|---|---|
| `aster_bridge.py` | server: auth, allowlist, guard, sanitize, audit |
| `public_schema.py` | **public layer** — allowlist, contracts, fail-closed sanitizer |
| `private_adapter.py` | **private layer** — internal ids, handle vault, audit; never serialized |
| `denylist.txt` | outbound vocabulary policy; bridge refuses to start without it |
| `ASTER_TOOL_MANIFEST.json` | sanitized public schemas (also served at `/manifest`) |
| `ASTER_OPENAI_TOOLS.json` | the same allowlist as OpenAI function tools, for pasting |
| `test_leakage.py` | leakage suite |
| `.private\` | ACL-locked: token, salt, handle map, audit, journal |

`.private\` has inheritance stripped and is granted to the host account only.
Nothing in it is reachable through any route; no operation reads it.

## The ChatGPT / Codex custom-tool route

The bridge binds loopback only, by design. **A cloud-hosted model cannot reach
`127.0.0.1` on this machine** — so the client must be something that already
runs *on this host*:

- **Codex CLI**, or
- **the ChatGPT desktop app** with a local tool/MCP shim, or
- any local agent process that holds the token and calls `/rpc`.

Do not attempt to reach it any other way. A tunnel, a reverse proxy or a
forwarded port would defeat the entire boundary — the loopback bind is the
outermost control, and it is the one that cannot be bypassed by a bug in the
layers above it.

Wiring it up:

1. `python aster_bridge.py --emit-openai` → writes `ASTER_OPENAI_TOOLS.json`,
   13 function-tool definitions matching the allowlist exactly.
2. Register those 13 tools in the local client's tool configuration.
3. Point every tool at `POST http://127.0.0.1:7891/rpc`, sending
   `{"verb": "<tool name with _ back to .>", "params": {…}}`.
4. Add the `Authorization: Bearer …` header — see the final step below.

Type mapping, bridge → JSON Schema (already applied in the emitted file):

| Bridge | JSON Schema |
|---|---|
| `handle`, `text`, `stamp`, `enum` | `string` (`enum` carries its values) |
| `flag` | `boolean` |
| `count` | `integer` |
| `list` | `array` |
| `shape` | `object`, `additionalProperties: false` |

---

## ⛔ THE FINAL STEP — THIS ONE IS YOURS

**Everything above is done. This is the only remaining action, and it must be
performed by you, at the keyboard.**

> **Read the bearer token out of**
> `C:\Users\lucys\Desktop\MUHLNICKEL_LOOM\bridge\.private\aster_token.txt`
> **and paste it into the local client's tool configuration as the
> `Authorization: Bearer <token>` header — then approve the tool registration.**

Equivalently, to print it to your own console:

```
python aster_bridge.py --show-token
```

**Why this step is not automated and must not be:**

- The token is the *only* thing standing between a local process and the
  capability surface. It is minted locally, stored under an ACL-locked folder,
  and is deliberately **never printed at start-up, never logged, never placed
  in any document, and never handed to any agent.**
- Approving the tool registration is the moment the capability surface is
  actually granted to an outside party. That decision is yours to make
  knowingly, not something to inherit from a script.

**Token handling:** treat it as a credential. Rotate by deleting
`.private\aster_token.txt` and restarting — a new one is minted and every
previously issued token stops working immediately. Never commit it, never
paste it into a chat window, never send it anywhere off this host.
