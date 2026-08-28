# grok.com revenue orchestrator

`route_grokcom_revenue_work` is the open Commons MCP seam for the operating
loop the owner requested:

```text
every Slack message
  -> deterministic work packet
  -> authenticated grok.com build / research / sales turn
  -> independent GPT review
  -> grok.com revision when needed
  -> fresh-main Git landing and exact readback
  -> next Slack or revenue action
```

The public MCP remains the one canonical server:

```text
https://commons-spark-mcp.vercel.app/mcp
```

There is no second server, credential store, identity check, allowlist, or
provider-specific token parameter. The connector that already receives a Slack
event passes its event object to this tool and posts the returned `slack_reply`
to `connector.reply_target`. The Grok surface receives `grokcom.prompt` and
returns its artifact manifest through `stage=GROKCOM_RESULT`. The existing
grok.com GitHub connection remains the code road; when grok.com exposes a remote
MCP connection field, point it at the same public URL above.

The tool also accepts an empty object and future free-form fields. Empty input
means “continue the highest-value open Commons revenue work”; unknown stage or
mode labels fall back to open intake and automatic routing. Schema metadata is
descriptive, never an admission check.

## Message contract

For every Slack `message` or `app_mention`, call:

```json
{
  "name": "route_grokcom_revenue_work",
  "arguments": {
    "stage": "INTAKE",
    "mode": "AUTO",
    "event": {
      "event_id": "Ev...",
      "channel": "C0BRGMDQB6G",
      "message_ts": "1787871538.126989",
      "thread_ts": "1787871538.126989",
      "author": "U...",
      "text": "the complete Slack message"
    }
  }
}
```

The same event always produces the same task ID and dedupe key. Every ordinary
message returns `post_reply=true`. A reply produced by this connector carries
`connector_origin=COMMONS_GROKCOM_REVENUE`; its echo is still processed but
returns `post_reply=false`, preventing a self-reply loop without filtering any
human or peer message.

## Build and review loop

1. `INTAKE` returns `GROKCOM_WORK`, an immediate Slack acknowledgement, and an
   exact grok.com prompt.
2. `GROKCOM_RESULT` requires the returned artifact manifest and creates a GPT
   review packet.
3. `GPT_REVIEW` returns the work to grok.com if any exact-byte, test,
   fresh-main, diff, secret, open-door, or zero-fabrication check is incomplete.
   A complete review returns the non-force fresh-main Git landing packet.
4. `GIT_LAND` records base/head/main SHAs, PR URL, exact path hashes, and tests,
   then returns `CONTINUE`; landing one item never stops the queue.

The tool constructs packets and truth labels. GitHub and Slack mutations remain
with their connected carriers, so the repository never receives their secrets.

## Revenue process

Research is useful only when it advances a buyer through a truthful process:

```text
DISCOVER -> QUALIFY -> DRAFT -> GPT_REVIEW -> SEND_BY_CONNECTED_CARRIER
-> REPLY -> DISCOVERY_CALL -> QUOTE -> ACCEPTANCE -> DELIVERY
-> PROCESSOR_REFERENCE -> CASH_READBACK
```

Each call may include `revenue` counters and exact `evidence_refs`. The output
keeps prospects, contacts, transports, replies, acceptance, processor state,
and cash separate. References remain `REFERENCED_NOT_INDEPENDENTLY_VERIFIED`;
the orchestrator never promotes a quote, payment link, processor reference, or
owner report to collected cash. It also tells research turns to return current
source URLs, dates, buyer identity, demonstrated pain, budget evidence, fit, and
a non-duplicative next action.

## Connector operating rule

Run one durable consumer over all message events, key retries by Slack event ID,
post each status in the originating thread, and keep consuming. Existing Commons
roads remain composed as-is: HUSK Slack-to-board, the grok.com GitHub connection,
the public Commons MCP, GPT verification, and Moth board-to-Slack. Do not remint
those roads and do not route this pool through Cursor, Grokbot, or a local Grok
CLI.
