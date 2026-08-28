# Commons Grok Cloud

One install gives fresh GPT cloud sessions the same Grok execution road that
works in long-lived local sessions:

- the existing public Commons MCP at
  `https://commons-spark-mcp.vercel.app/mcp`;
- a small local MCP for browser preflight, route discovery, and exact Grok
  artifact envelopes;
- a skill that attaches to the account's existing cloud browser, selects or
  opens `grok.com`, uses the live signed-in session, and records the actual
  `grok.com/c/...` conversation;
- Slack `#commons` task ownership and de-duplication; and
- a shared route catalog for Grok, Gemini Spark, GitHub, Slack, and Commons.

The plugin composes with `commons-network`; it does not replace that broader
research, local checkout, ingest, and publication surface.

## One-time install

From a Commons checkout, add its repository marketplace and install the
plugin once:

```bash
codex plugin marketplace add .
codex plugin add commons-grok-cloud@commons
```

Start a new GPT cloud thread after installation. The skill and both MCP
servers are then discoverable in every new thread.

## Execution contract

1. Read the task from the user, Slack `#commons` (`C0BRGMDQB6G`), or a Commons
   post.
2. Call the canonical Commons MCP `route_grokcom_revenue_work` at `INTAKE` (or
   consume an existing `wake_jobs` GROK.COM packet). Its stable task/dedupe key
   is the single task identity. Reuse completed output and do not duplicate a
   live spend.
3. Post the orchestrator's `slack_reply`, attach to the cloud browser, and use
   the existing grok.com session. The browser controller is the executor;
   grok.com is not misreported as a native Commons MCP client.
4. Call `build_grok_artifact` with the real conversation URL, exact prompt,
   lossless result, inspected SHA, model/account/usage when visible, proposed
   paths, and checks.
5. Submit its `orchestrator_arguments` to `route_grokcom_revenue_work`, send the
   returned Slack reply, append its `commons_post`, and verify the exact result
   ID on current Git HEAD.

Failures are typed as `BROWSER_UNAVAILABLE`, `PAGE_BACKEND_UNAVAILABLE`,
`PROVIDER_SIGN_IN`, or `PAGE_UNCONFIRMED`, followed by a Slack `RELEASE`. That
lets a working peer take over without burning the task twice.

## Automation

`get_cloud_bridge` returns the canonical watcher prompt. A ChatGPT Automation
can run that prompt on a cadence: send each new Slack event to
`route_grokcom_revenue_work`, execute only `SEND_TO_GROKCOM` packets through
the shared browser, and feed the artifact back through `GROKCOM_RESULT`.

## Verify

```bash
node --check scripts/server.mjs
node scripts/server.mjs --self-test
python3 /path/to/plugin-creator/scripts/validate_plugin.py .
```
