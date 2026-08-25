# RESOURCE LEDGER — cache is not capacity

Slack `1787637936.134649` (2026-08-25), DEMON live
compute/connector board:

> USE THESE, DO NOT COUNT CACHE AS CAPACITY
> Keep a live resource ledger with evidence timestamp, auth
> surface, exact safe probe, rate/plan boundary, assigned
> backlog outcome, and last receipt.

A Slack utilization report is **CLAIMED**. This leftover is
the ledger. It does not write financial, messaging, account,
or production connectors. It does not deploy Vercel. It does
not actuate `state.vscdb`. titan: **NOT_WRITTEN**.

Do not remint a DEMON taking with no `p/{id}.md`. Do not remint
`rivet-ship-connector-reval-20260825-01`. That leftover measured
MCP provisioned-vs-live. This leftover measures **compute
capacity** and refuses to call cache "connected."

Companion actual-build utilization report:
[`ground/OWNER_MACHINE_BUILD_SWEEP.md`](OWNER_MACHINE_BUILD_SWEEP.md).

Owner correction: Claude remains available only for implementation or
informational evidence, never as a tester/verifier. Every Claude zero
from the 2026-08-25 incident window is **RETRACTED**. Do not repeat a
derived conclusion or owner characterization from those results.

## Measure

Instrument: `host/resource_ledger.py`. Stdlib only. Catalog:
`ground/RESOURCE_LEDGER.json`. Door: [`ledger.html`](../ledger.html).
Names and states only. No tokens, env, or emails.

```bash
python3 host/resource_ledger.py
python3 host/resource_ledger.py --root .
python3 host/resource_ledger.py --self-test
```

Required fields on every row:

- evidence timestamp
- auth surface
- exact safe probe
- rate/plan boundary
- assigned backlog
- last receipt

Capacity states:

- **LIVE** — this session answered a read-only probe
- **CACHE** — Aug 21 / provisioned list, not live here
- **NOT_VERIFIED** — claimed or cached, probe failed or absent
- **UNMEASURED** — no claim and no probe. Absence is not stillness
- **FORBIDDEN** — financial / messaging / account / production write

Hugging Face with no token file and no CLI is **NOT_VERIFIED**.
Vercel with zero projects and no CLI is **NOT_VERIFIED**.
A production deploy is refused.

## This session (2026-08-25 cloud)

Read-only probes that answered:

- GitHub — `get_me` + official main `62c46802e`
- Slack — read `#commons` thread `1787637936.134649`
- Grok/Cursor — this harness is Cursor Grok 4.6

Not capacity here:

- `grok.exe` — binary absent
- Claude CLI — binary absent on this cloud-scoped row and not probed on the
  owner machine by this row; Commons still cannot doorbell Claude. Assigned
  backlog is untrusted candidate implementation only. Tester / verifier /
  review authority is false.
- Sites — no Sites CLI; swarm flight recorder already on main
- Vercel — CLI absent; Hobby zero-projects claim; deploy refused
- Hugging Face — no token file, no CLI

`~/.cursor/mcp.json` absent. Forbidden writes skipped.

Live-compute-board / cache-as-capacity / resource-ledger /
five-high-value-surfaces / huggingface-not-verified talk
without this leftover is **CLAIMED**. Missing instrument is
**NOT_LANDED**.

Possessing the link is authorization. No auth. No gate.
