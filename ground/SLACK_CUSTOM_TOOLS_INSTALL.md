# Slack custom tools install — @facebook drives Facebook from the tagged body

Owner hub `1788319779.597119`: if the harness has Slack but not Facebook, `@facebook` is a **Slack custom tool**, not a fake in-harness Facebook call. Same shape for every catalog tag. Provider sessions only Bryce can complete go to existing `#needs-bryce` (`C0BRX6EV739`). That is not a Commons admission gate.

Peer `cursor-slack-service-tags-20260902-01` already landed the catalog and router. This card is the **install** lane: public Slack CLI, Bolt custom function `drive_tagged_service`, slash command `/svctool`, exact-action login queue.

## What gets installed

- Public Slack CLI at `~/.slack/bin/slack` (this desk installed v4.7.0).
- App name **Commons Service Tools**.
- Custom function `drive_tagged_service` (tag + body → drive that provider).
- Slash command `/svctool facebook post the drop tonight`.
- App mention / channel text with `@facebook` (and every catalog tag) runs the same driver.
- Missing provider sessions post an exact-action item to `#needs-bryce` with an official `https://` console URL. Never copy secrets into Slack or git.

## Commands

```bash
python3 host/slack_custom_tools_install.py --status
python3 host/slack_custom_tools_install.py --write-manifest
python3 host/slack_custom_tools_app.py --text "@facebook post the drop tonight"
python3 host/needs_bryce_login_queue.py --tag facebook --body "post the drop tonight"
```

Slack CLI login (agent-driven, challenge still needs Bryce):

```bash
slack login --no-prompt
# paste /slackauthticket … in the workspace, reply in #needs-bryce with the challenge
slack login --ticket <ticket> --challenge <code>
slack run --org-workspace-grant=all
```

Live Graph/API calls stay opt-in. Dry-run default is `READY` when a session env var is present, `NEEDS_OWNER_SIGNIN` when it is not.

## Do not

- Steal `host/slack_service_tag.py` / `ground/SLACK_SERVICE_TAGS.*` / `slack-tags.html`.
- PUT `board_ingest.py`.
- Paste passwords, app secrets, or session tokens into Slack.
- Treat `#needs-bryce` as a Commons login form.
