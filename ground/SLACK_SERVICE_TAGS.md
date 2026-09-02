# Slack service tags

Owner hub `1788319779.597119` (2026-09-02): make Slack do the work. If a model has a Slack connector but not Facebook, `@facebook` is a Slack custom-tool road. The custom tool takes the message and drives Facebook from the tagged body. Same shape for every service. Provider sessions Bryce must complete in a browser go to the existing owner-exclusive channel, not a new Commons lock.

This is a routing convention. `gate` is false. Missing tags, missing tools, or missing speaker metadata never reject a Commons post. Possessing a Commons link is still authorization for the open door.

## Shape

1. Write the work in Slack. Prefix the service with `@tag` (`@facebook post the drop`).
2. If this harness already has that provider tool, it may run in-harness.
3. If it does not, emit a Slack custom-tool job for `@tag` with the remainder of the body. Do not pretend an in-harness Facebook call exists.
4. If the provider still needs a Bryce browser or Cursor connector session, post one `OWNER_BLOCKER` root in `#provider-sign-in` (`C0BUFA9G23E`). `#needs-bryce` stays the other owner-exclusive queue. Neither is Commons authentication.

Reserved Slack broadcast tokens are not services: `here`, `channel`, `everyone`, `group`, `reminders`, `slackbot`. User mentions (`<@U…>`) are not service tags.

Unknown `@tags` still emit a job with road `UNKNOWN`. That is expansion, not a rejected verb.

Aliases (`@twitter` → `x`, `@fb` → `facebook`) canonicalize before lookup. Remainder strips the original spelling.

## Owner sign-in queue

Reuse `#needs-bryce`. Do not invent a second Commons identity. Do not copy secrets into Slack, Git, or receipts. After Bryce completes the provider session, the peer resumes the tagged job.

Machine map: [SLACK_SERVICE_TAGS.json](./SLACK_SERVICE_TAGS.json). Helper: [host/slack_service_tag.py](../host/slack_service_tag.py). Worker: [host/slack_service_tag_worker.py](../host/slack_service_tag_worker.py). Door: [slack-tags.html](../slack-tags.html).

Installed 2026-09-02 (`cursor-slack-service-tools-install-20260902-01`): `#provider-sign-in` `C0BUFA9G23E`, Slack list `F0BU7D9RBL5`. Slack management is the agents' job. Provider sessions this process cannot complete queue on that channel. `#needs-bryce` stays the other owner-exclusive queue. Neither is Commons authentication.

Complementary CLI/Bolt install on main (peer `cursor-slack-custom-tools-install-20260902-01`, PR 7452): `host/slack_custom_tools_install.py`. This catalog does not steal those unique paths. Their Slack CLI challenge stays on `#needs-bryce`.

GOAT `#provider-sign-in` `1788321949.478239`: MagicPath connector tools-live in GOAT's harness. Cloud seats `bc-73365238` and `bc-63f55b0a` independently measured GetDynamicTools with no `magicpath` namespace. `@magicpath` stays a Slack custom-tool remainder to that desk. Do not reopen the MagicPath NEED. Do not pretend an in-harness MagicPath call exists here. Not a Commons login. Second-seat receipt: `cursor-slack-magicpath-seat-bc63f55b0a-20260902-01`.

GOAT `#provider-sign-in` `1788322480.169879`: Notion Cursor connector tools-live in GOAT's harness. Cloud seats `bc-73365238` and `bc-f49eebc7` independently measured GetDynamicTools with no `notion` namespace. `@notion` stays a Slack custom-tool remainder to that desk. Commons Spark MCP `https://commons-spark-mcp.vercel.app/mcp` measured HTTP 200 / no auth from both seats. The Notion-side Custom MCP field is not visible here, so this is not `OWNER ACTION DONE`. Do not reopen the Notion NEED. Not a Commons login. First receipt `cursor-slack-notion-peer-connected-20260902-01` stays blob `934361c7`. Second-seat receipt: `cursor-slack-notion-seat-bcf49eebc7-20260902-01`.
