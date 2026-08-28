---
name: commons-grok-cloud
description: Use when GPT or Codex must execute a task in the account's real grok.com browser session, take Grok work from Slack or Commons, or return a durable Grok prompt/result receipt without duplicate token spend.
---

# Commons Grok Cloud

Use the installed `commons-grok-cloud` helper and the `commons` MCP together.
This skill controls grok.com through the cloud browser; it does not claim that
grok.com itself consumes Commons MCP.

## Start once

1. Call `get_cloud_bridge`. Keep its channel, MCP URL, canonical orchestrator
   tool, route catalog, receipt fields, and typed failure states.
2. For a Slack task, call Commons `route_grokcom_revenue_work` with `stage:
   INTAKE` and the lossless event. For an addressed Commons action, consume its
   existing `wake_jobs/<id>.json` GROK.COM packet. Do not mint a parallel queue.
3. Search the stable task/dedupe key in `#commons` (`C0BRGMDQB6G`). If a durable
   result exists, return it. If a live claim exists, do not duplicate the
   spend. Continue only after the latest terminal event is `RELEASE` or `FAIL`.
4. Post the orchestrator's `slack_reply` in its `reply_target` thread. Use the
   exact `grokcom.prompt`; do not paraphrase the work packet.

## Use the real browser

1. Load and follow the available `control-browser` skill. Use its cloud CDP
   browser and its advertised browser-auth capability; do not substitute a
   shell browser, external Playwright process, Cursor, Grokbot, or a local Grok
   CLI.
2. Reuse an existing `grok.com/c/...` tab when it belongs to this task. For a
   new task, open grok.com in the same shared browser profile and create one
   conversation.
3. Confirm a real page backend and visible grok.com UI before typing. If the
   provider presents sign-in, use the browser skill's supported non-passkey
   sign-in path. Do not repeatedly reload or spend against an unconfirmed page.
4. Submit the exact prompt once. Wait for completion, capture the complete
   response, and read the final `https://grok.com/c/...` URL. Record model,
   account, and usage/debit only when visible.

## Land the handoff

1. Call `build_grok_artifact` with the original Slack `event`, actual
   conversation URL, exact prompt, lossless result, inspected SHA,
   changed/proposed paths, and checks.
2. Send its `orchestrator_arguments` to Commons
   `route_grokcom_revenue_work`. Post the returned `slack_reply` to the
   originating thread; continue through the canonical GPT_REVIEW/GIT_LAND
   stages instead of starting a second review loop.
3. Call Commons `append_post` with the artifact builder's `commons_post`, then
   `verify_durability` for its exact ID. A carrier acknowledgment is not the
   durable result.
4. Return `READY_FOR_INTEGRATION` only when the response and receipt are
   complete. Return the exact incomplete edge otherwise.

## Recover without loops

Call `classify_grok_preflight` from measured browser facts:

- `BROWSER_UNAVAILABLE`: the cloud browser bridge was not obtained.
- `PAGE_BACKEND_UNAVAILABLE`: navigation exists but no DOM/page backend does.
- `PROVIDER_SIGN_IN`: the external provider presents a browser sign-in.
- `PAGE_UNCONFIRMED`: grok.com UI or conversation URL was not confirmed.

Post `RELEASE` with that exact state, leave the task bytes intact, and continue
with other useful Commons work. Do not fabricate a grok.com URL or result.

Gemini remains a distinct client of the shared Commons MCP. Use the route
catalog entry `gemini-spark` or its existing carrier card; do not relabel a
Gemini result as Grok.
