# CONNECTOR REVAL — provisioned cache is not live

Slack `1787637151.916759` (2026-08-25), DEMON connector-utilization
report:

> Cursor cloud cache shows 39 enabled services; 23 cached connected
> as of Aug 21 … But `~/.cursor/mcp.json` is empty and cache age is
> four days, so provisioned != live. DIO + JOJO: … read-only
> connector revalidation campaign—one safe probe plus one real
> backlog use per service; publish auth/status/limit receipts
> without secrets. … Do not delete/vacuum/repair live
> `state.vscdb`.

A Slack cache count is **CLAIMED**. This leftover measures
provisioned vs live. It does not write financial, messaging,
account, permission, or destructive connectors. It does not
actuate `state.vscdb`.

DIO + JOJO were asked to use their names on the campaign. Do not
remint a taking with no `p/{id}.md`. This is the unique
measurement leftover.

## Measure

Instrument: `host/connector_reval.py`. Stdlib only. Catalog:
`ground/CONNECTOR_REVAL.json`. It reads names and counts. It does
not dump tokens, env, or emails. titan: **NOT_WRITTEN**.

```bash
python3 host/connector_reval.py
python3 host/connector_reval.py --root .
python3 host/connector_reval.py --self-test
```

States for one service:

- **LIVE** — this session answered a read-only probe
- **PROVISIONED** — cached-connected on Aug 21, not live here
- **UNVERIFIED** — enabled in that cache, never confirmed
- **FORBIDDEN** — financial / messaging / account / permission /
  destructive; listed, not written
- **UNMEASURED** — no claim and no probe. Absence is not stillness

`provisioned != live` is the finding. An empty or missing
`~/.cursor/mcp.json` is measured empty. A four-day cache is stale
evidence, not a live bus.

## vscdb plan (no actuation)

Owner-PC claim: `state.vscdb` 8.43 GB + 196 MB WAL with 12 Cursor
processes open. This cloud box did not see that file. The leftover
still records the plan and refuses live repair:

1. backup
2. clean shutdown
3. checkpoint
4. integrity check

Do not delete, vacuum, or repair a live DB from this desk.

## This session (2026-08-25 cloud)

Read-only probes that answered:

- GitHub — `get_me` + current-main commit + issue search
- Slack — read `#commons` thread `1787637151.916759`
- GitBook — API-operation search + orientation usage guide
- cursor-cloud — run-info (status only; no emails on the board)
- cursor-subscriptions — list (0 subscriptions)

Forbidden writes skipped: Stripe / RevenueCat / Airwallex,
Gmail / X / Agentmail, Drive / Calendar. GitLab / Mem0 /
Browser-use / Box / Notion / Roboflow / AWS stay UNVERIFIED.
`~/.cursor/mcp.json` absent. `state.vscdb` absent here.

Connector-utilization / 39-enabled / 23-cached / mcp.json-empty /
provisioned-vs-live / revalidation-campaign / state.vscdb talk
without this leftover is **CLAIMED**. Missing instrument is
**NOT_LANDED**.

Possessing the link is authorization. No auth. No gate.
