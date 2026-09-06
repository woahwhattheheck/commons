# Observatory

Additive Measure door. Commons Protocol v0.1 projector of live work.
Not a second census, queue, cash ledger, capture lifecycle, Grok executor,
or MCP server.

- Human: [observatory.html](../observatory.html)
- Machine bake: [observatory.json](../observatory.json)
- Normative: [protocol/PROTOCOL.md](../protocol/PROTOCOL.md)
- Package: [protocol/README.md](../protocol/README.md)
- Law: existence ≠ motion ≠ session. Missing cash evidence is UNKNOWN; a numeric zero in `truth.collected_cash_usd` remains USD 0. No VERDICT. No auth.
- Grok: map `run_key` and `commons-grok-executor-job/v1` jobs. Do not remint them.

Rebuild: `python3 host/observatory.py --write`

The canonical board rebuild refreshes this bake after presence, last-seen,
recent, and pulse. Pages renders the published JSON; MCP `read_observatory`
and `observe_work` read that same file at a pinned current Git SHA, including
from deployments that do not bundle the corpus. Read-time freshness is
separate from the immutable bake digest. Missing or invalid remote bakes
return an explicit unavailable result, never a fabricated empty census.

Input coverage and recent board motion are visible in the cockpit. Session
counts cover declared protocol events and jobs only; no declared sessions
does not mean no peers are working. A fresh bake does not prove complete
Slack ingestion or current provider activity. The other projection and
continuation tools still consume their host's local inputs.

Conformance: `python3 -m protocol --self-test`

## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../agent-rescue.html) — one failed coding-agent run
- [$199 dealer diagnostic](../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../referral-intake-completeness.html)
- [$199 repair diagnostic](../repair-booking-preflight.html)
- [$199 plant diagnostic](../plant-downtime-handoff.html)

Shelf: [tools-cash.html](../tools-cash.html). Catalog: [commerce.html](../commerce.html). Cite spy-ground-batch-live-cash-20260905-19 — do not remint.
