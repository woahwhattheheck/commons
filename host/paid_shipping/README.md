# Free Commons shipping monitor candidate

Publish `host/paid_shipping/{worker.mjs,rules.mjs,schema.sql,runner.mjs}` and
`.github/workflows/commons-shipping-monitor.yml` to the **public**
`woahwhattheheck/commons` repository. Keep tests in source if useful. The
workflow uses a standard Ubuntu runner, Node 22, no package install, and no
artifact or cache upload. Do not enable it until a manual `workflow_dispatch`
actually starts and succeeds on this account; billing or account settings may
block Actions even though GitHub's public-runner pricing is free.

Set repository Actions secrets `COMMONS_GITHUB_TOKEN` (the existing shared
GitHub credential with private `commons-ship-enforcer` read/write and publisher
access), `SLACK_BOT_TOKEN`, and `TYPESAFE_API_KEY` from the shared secure vault. Never check token
values into either repository or print them in Actions logs. The runner reads
only the three configured Slack channels. Before touching Slack or state, each
run verifies repository metadata says `private: true` and
`visibility: private`. All persisted state, including
intermediate thread content, lives only at private
`woahwhattheheck/commons-ship-enforcer:paid-work/shipping-state.json`.
It writes that file through the required account publisher `file.put` route
using the previous GitHub Contents SHA and a deterministic operation ID.
No Cloudflare monitor/D1 call is made by this runner. Its SQLite database is
in memory for each tick; a version 2 gzip+base64 JSON envelope with a raw
SHA-256 checksum is the private durable snapshot. Legacy version 1 plaintext
JSON loads without dropping rows. Decompression is bounded at 32 MiB; an
oversized or invalid snapshot fails rather than silently discarding state.
The publisher request sets `User-Agent: Commons-Shipping-Enforcer/1.0`.

For each new or changed nonbaseline candidate thread, the runner sends the
peer thread text to TypeSafe System One (`jev-latest`) as one typed choice:
`submit_own_patch`, `follow_existing_pr`, `complete_claim_step`,
`repair_route`, or `no_followup`. Only fixed local notice text can be posted;
JEV cannot write prose or authorize publication. Existing GitHub provider
checks still verify our upstream PR before a notice. A temporary JEV API error
uses the original static rules for that thread and reports
`jev_status: degraded_static_fallback` plus call, error, and input-token counts
in the aggregate run log. The required key is checked at runner start.

Native nonincident diagnostic ingress changes from the disabled Cloudflare
`/v1/operator-notice` URL to a private per-notice Git file. For a validated
minimal notice object with exactly the keys `notice_id`, `reason_code`,
`tool_name`, and optional `operation_id`, `repository`, `issue_number`, publish
its JSON as `paid-work/shipping-operator-notices/<notice_id>.json` in the
private repository using the existing central publisher `file.put` operation.
`notice_id` must be lowercase 64-hex, `reason_code` lowercase letters and
underscores up to 80, `tool_name` safe identifier up to 100, repository
`owner/name`, issue number positive integer. Do not include prose, commands,
paths, draft content, or secrets. Use a stable operation ID derived from the
notice ID. A repeated same-ID file is an acknowledged receipt after provider
readback; a different payload at that path is a conflict. The runner imports
up to four unseen notices per tick from the private Git tree and uses the
existing Slack outbox/readback marker to deduplicate delivery.

The runner does not read Cloudflare D1 incidents. A blocked incident needs an
equivalent content-free private notice from the publisher/native caller if
Slack operator routing is wanted. The authenticated publisher incident record
and Bryce's private incident email path remain authoritative. Never send an
incident description into this diagnostic ledger.

Run tests from the candidate root:

```sh
node --test --test-concurrency=1 host/paid_shipping/*.test.mjs
```

The test concurrency flag avoids independent suites replacing the global
`fetch` fixture simultaneously. The live read probe confirmed that Slack
`conversations.replies` accepts GET with query parameters and rejects POST
JSON for the same thread; the worker uses GET for both history and replies.

If this account blocks GitHub Actions, the same `runner.mjs` can run with a
hidden Windows Task Scheduler job every five minutes using the shared vault
credentials. That remains independent of a Codex account/session but depends
on the PC staying online. Verify an actual scheduled run and private Git state
readback before declaring either schedule live.
