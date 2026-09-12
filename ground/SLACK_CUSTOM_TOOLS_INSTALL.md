# Slack custom tools install — @facebook drives Facebook from the tagged body

Owner hub `1788319779.597119`: if the harness has Slack but not Facebook, `@facebook` is a **Slack custom tool**, not a fake in-harness Facebook call. Same shape for every catalog tag. Provider sessions only Bryce can complete go to installed `#provider-sign-in` (`C0BUFA9G23E`); owner-exclusive non-provider actions such as the Slack CLI challenge remain in `#needs-bryce` (`C0BRX6EV739`). Neither is a Commons admission gate.

Peer `cursor-slack-service-tags-20260902-01` already landed the catalog and router. This card is the **install** lane: public Slack CLI, Bolt custom function `drive_tagged_service`, slash command `/svctool`, exact-action login queue.

## What gets installed

- Public Slack CLI at `~/.slack/bin/slack` (this desk installed v4.7.0).
- App name **Commons Service Tools**.
- Custom function `drive_tagged_service` (tag + body → drive that provider).
- Slash command `/svctool facebook post the drop tonight`.
- App mention / channel text with `@facebook` (and every catalog tag) runs the same driver.
- Missing provider sessions post a secret-free blocker to `#provider-sign-in`, following the installed service-tag catalog. Never copy secrets into Slack or git.
- Slack CLI `/slackauthticket` challenge handling remains owner-exclusive in `#needs-bryce`.

## Commands

```bash
python3 host/slack_custom_tools_install.py --status
python3 host/slack_custom_tools_install.py --write-manifest
python3 host/slack_custom_tools_cli_project.py --status
python3 host/slack_custom_tools_cli_project.py --write-project
python3 host/slack_custom_tools_app.py --text "@facebook post the drop tonight"
python3 host/needs_bryce_login_queue.py --tag facebook --body "post the drop tonight"
```

Slack CLI login (agent-driven, challenge still needs Bryce):

```bash
slack login --no-prompt
# paste /slackauthticket … in the workspace, reply in #needs-bryce with the challenge
slack login --ticket <ticket> --challenge <code>
cd host/slack_custom_tools_cli
slack manifest validate --source local
slack app install --org-workspace-grant=all   # CLI wraps apps.manifest.create
slack run --org-workspace-grant=all
```

The CLI project lives at `host/slack_custom_tools_cli/` (hooks + get-manifest + start). It does **not** replace the peer HTTP worker `host/slack_service_tag_worker.py`. `.slack/apps.json` is gitignored.

Live Graph/API calls stay opt-in. Dry-run default is `READY` when a session env var is present, `NEEDS_OWNER_SIGNIN` when it is not.

## Do not

- Steal `host/slack_service_tag.py` / `ground/SLACK_SERVICE_TAGS.*` / `slack-tags.html`.
- PUT `board_ingest.py`.
- Paste passwords, app secrets, or session tokens into Slack.
- Treat `#provider-sign-in` or `#needs-bryce` as a Commons login form.

## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../agent-rescue.html) — one failed coding-agent run
- [$199 dealer diagnostic](../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../referral-intake-completeness.html)
- [$199 repair diagnostic](../repair-booking-preflight.html)
- [$199 plant diagnostic](../plant-downtime-handoff.html)

Shelf: [tools-cash.html](../tools-cash.html). Catalog: [commerce.html](../commerce.html). Cite spy-ground-batch-live-cash-20260909-04 — do not remint.

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../titanmcp.html). Cite Latch Pad KEEP. Submit/YouTube wait Bryce exact go.