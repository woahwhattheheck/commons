# Slack CLI project leftover — Commons Service Tools

Peer land `65dc46fa5` already minted the Slack CLI project at
`host/slack_custom_tools_cli/` plus `host/slack_custom_tools_cli_project.py`
and receipt `p/cursor-slack-custom-tools-cli-project-20260902-01.md`.
That receipt is **not reminted**. Peer readback `0e6ad49f` / blob `8fcc3d36`
is **not reminted**.

This card is the complementary **integrations** cwd, next to
`integrations/slack_service_tags/`, so `slack run` also has a project beside
the service-tag worker install.

## Paths

- Peer (already on main): `host/slack_custom_tools_cli/`
- Compose (this leftover remainder): `integrations/slack_custom_tools/`
- Entry: `integrations/slack_custom_tools/app.py` imports
  `host/slack_custom_tools_app.register` (does not remint the driver)
- Hooks: `.slack/hooks.json` + local `hooks/get_manifest.py` (no npm)

## Login

Still `#needs-bryce` (`C0BRX6EV739`). Not a Commons admission gate.

```bash
# peer cwd (already on main)
cd host/slack_custom_tools_cli && slack run --org-workspace-grant=all
# compose cwd
cd integrations/slack_custom_tools && slack run --org-workspace-grant=all
```

Do not paste a password, app secret, or session token into Slack or git.
