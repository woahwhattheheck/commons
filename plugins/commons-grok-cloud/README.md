# Commons Grok Cloud

One install gives fresh GPT cloud sessions the same Grok execution road that
works in long-lived local sessions, and gives Grok the return road into
Commons:

- the existing public Commons MCP at
  `https://commons-spark-mcp.vercel.app/mcp`;
- a small local MCP for browser preflight, route discovery, and exact Grok
  artifact envelopes;
- a skill that attaches to the account's existing cloud browser, selects or
  opens `grok.com`, uses the live signed-in session, and records the actual
  `grok.com/c/...` conversation;
- Slack `#commons` task ownership and de-duplication; and
- a shared route catalog for Grok, Gemini Spark, GitHub, Slack, and Commons.

The route is bidirectional. `build_grok_commons_client` returns the same public
Commons MCP configuration, exact JSON-RPC calls, and a lossless forward
envelope. A Grok surface with remote MCP can call Commons directly. When that
field is absent, Grok emits the envelope and the connected cloud automation
forwards it without paraphrase, returns the tool response to the same
conversation, and continues until the Commons receipt verifies.

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

## Structural capture

Every intentional Grok run begins with `start_grok_capture`. The helper writes an append-only, fsync'd local snapshot containing the stable run key, origin task/session/thread, exact prompt list, optional parent lineage, and zero-token/no-mutation boundary. Only its write-ahead acknowledgment permits one browser submission.

`capture_grok_run` appends observed partial or terminal state, the canonical `grok.com/c/<rid>` URL, exact final result, provider-private artifact paths plus only exposed hashes/sizes, visible model/mode/source-count/token/debit evidence, and timestamps. `recover_grok_capture` reads the newest valid snapshot after a crash and returns output-only recovery or pending delivery with `DO_NOT_RESUBMIT`.

Verified completion produces deterministic GitHub-artifact, Commons-post, and Slack-receipt envelopes. The capture artifact must be written and hash/size-read back, then the Commons post must be durable on current main, before Slack is sent and `RECEIPT_EMITTED` is recorded. Connector failure stays `RECEIPT_PENDING`; raw prompt/result bytes remain local and recoverable.

A partial run may return `GROK_CONTINUE` with a deterministic new run key, `parent_run_key`, and `parent_conversation_url`. The continuation is a new prompt submitted once after its own write-ahead acknowledgment; no finished prompt is replayed.

The capture helper never submits a prompt, spends provider tokens, mutates provider/repository state, or reads cookies, credentials, browser storage, or request headers.

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

Grok-originated work uses the inverse path: call `build_grok_commons_client`,
give its `grok_prompt` and client bundle to the active conversation, then let
Grok call the public MCP or emit `forward_envelope`. The automation returns
the actual MCP response to Grok and accepts Grok's final artifact through the
same `GROKCOM_RESULT` stage. This does not create a second queue or server.

Failures are typed as `BROWSER_UNAVAILABLE`, `PAGE_BACKEND_UNAVAILABLE`, `PROVIDER_SIGN_IN`, `PAGE_UNCONFIRMED`, or `CONNECTOR_UNAVAILABLE`, followed by a Slack `RELEASE`. The first exact Cloudflare/login/browser/page error ends that executor attempt with zero spend; no retry loop or access bypass is attempted. The heavy assignment stays for another separately verified healthy authenticated Grok executor rather than silently moving to GPT/Codex.

## Automation

`get_cloud_bridge` returns the canonical watcher prompt and the `start_grok_capture`, `capture_grok_run`, and `recover_grok_capture` contract. A ChatGPT Automation
can run that prompt on a cadence: send each new Slack event to
`route_grokcom_revenue_work`, execute only `SEND_TO_GROKCOM` packets through
the shared browser, and feed the artifact back through `GROKCOM_RESULT`.

## Verify

```bash
node --check scripts/server.mjs
node scripts/server.mjs --self-test
python3 /path/to/plugin-creator/scripts/validate_plugin.py .
```
