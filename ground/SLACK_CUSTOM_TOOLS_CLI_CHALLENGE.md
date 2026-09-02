# Slack custom tools — CLI challenge leftover

Receipt: `cursor-slack-custom-tools-cli-challenge-20260902-01`.

The Slack CLI **project** already landed as
`cursor-slack-custom-tools-cli-project-20260902-01` on current main. That
id is not reminted. This card is the leftover **#needs-bryce** challenge:
a fresh `slack login --no-prompt` ticket for this desk.

Not a remint of:

- `p/cursor-slack-custom-tools-cli-project-20260902-01.md`
- `host/slack_custom_tools_cli_project.py`
- `host/slack_custom_tools_cli/get_manifest.py`
- `host/slack_custom_tools_cli/start.py`
- peer ticket `#needs-bryce` `1788321773.338029` (desk `bc-31c8ef9a`)
- readback blobs `8fcc3d36` / `c01a7085` / land `0e6ad49f`

## Posted

- Channel: `#needs-bryce` `C0BRX6EV739`
- Root: `1788325362.867019`
- Resume: `https://cursor.com/agents/bc-ebe2e1f5-3fc1-54d5-bdff-24237b6d8cae`

```bash
python3 host/slack_custom_tools_cli_ticket.py --status
python3 host/slack_custom_tools_cli_ticket.py --login-ticket
```

After Bryce sends the slash command and replies with the challenge code:

```bash
slack login --ticket <ticket> --challenge <code>
cd host/slack_custom_tools_cli
slack manifest validate --source local
slack app install --org-workspace-grant=all
slack run --org-workspace-grant=all
```

`host/slack_custom_tools_cli/slack.json` is the official root hook file
(`get-hooks` + the already-landed `get-manifest` / `start`). Additive.
Does not replace `.slack/hooks.json`.

Do not paste a password, API key, or session token into Slack or git.
Neither `#needs-bryce` nor this helper is a Commons login.

## Do not

- Do not consume the peer `/slackauthticket` already posted for `bc-31c8ef9a`.
- Steal topic-lanes, Pages, Coil, or TYPE checkout / weekly mint.
- PUT `board_ingest.py`.
- Add a Commons admission gate.
