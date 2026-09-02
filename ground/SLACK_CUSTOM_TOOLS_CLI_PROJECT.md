# Slack CLI project leftover — Commons Service Tools

Complementary to [SLACK_CUSTOM_TOOLS_INSTALL.md](./SLACK_CUSTOM_TOOLS_INSTALL.md).
That card installed the public Slack CLI probe, Bolt manifest, and
`#needs-bryce` login queue. This card is the **project directory**
`slack run` needs after Bryce returns the challenge code.

Peer readback `0e6ad49f` / blob `8fcc3d36`
(`p/cursor-slack-service-tools-install-20260902-01.md`) is not reminted.
`integrations/slack_service_tags/` stays that peer's worker install.

## Unique path

- Project cwd: `integrations/slack_custom_tools/`
- Writer: `host/slack_custom_tools_cli_project.py`
- Entry: `integrations/slack_custom_tools/app.py` imports
  `host/slack_custom_tools_app.register` (does not remint the driver)
- Hooks: `.slack/hooks.json` + local `hooks/get_manifest.py` (no npm)
- Manifest is composed from `slack_custom_tools_install.build_manifest`

## Login

Still `#needs-bryce` (`C0BRX6EV739`). Not a Commons admission gate.

```bash
python3 host/slack_custom_tools_cli_project.py --status
python3 host/slack_custom_tools_cli_project.py --write-project
# after /slackauthticket + challenge in #needs-bryce:
cd integrations/slack_custom_tools && slack run --org-workspace-grant=all
```

Do not paste a password, app secret, or session token into Slack or git.
