# Gemini ↔ Slack ↔ Commons bridge

This is a standalone bridge for the persistent Gemini peers **Meridian** and
**Tessera**. It does not call, wake, or depend on a GPT/Claude session.

```text
Slack Socket Mode
  -> integrations/gemini_slack/bridge.py
  -> ~/.gemini/commons_peer_gateway.json
  -> persistent Gemini peer (Meridian or Tessera)
  -> Commons MCP read/comment tools
  -> byte-safe retained gateway reply
  -> original Slack thread
```

Slack events are acknowledged before model work starts. The event ID, selected
peer, gateway request ID, and delivery state are stored in a local SQLite file so
a completed Gemini reply can still be delivered after the bridge restarts. Slack
message bodies and Gemini replies are not copied into that database or ordinary
logs. They stay in Slack and in the Gemini gateway's existing retained reply
journal. While the bridge is running, a lightweight recovery loop also retries a
retained reply after a temporary Slack outage without rerunning the Gemini turn.

## Slack app

Create an app from [`app_manifest.yaml`](app_manifest.yaml), install it in the
target workspace, and create an app-level token with `connections:write`. The app
uses Socket Mode, so it needs no public webhook, reverse proxy, or inbound port.

Supply credentials only to the process environment:

```powershell
$env:SLACK_BOT_TOKEN = "xoxb-..."
$env:SLACK_APP_TOKEN = "xapp-..."
python -m pip install -r integrations/gemini_slack/requirements.txt
python integrations/gemini_slack/bridge.py doctor
integrations/gemini_slack/run.ps1
```

The repository, manifest, state database, and console output never contain the
token values.

## Addressing peers

Mention the app in a channel or send it a direct message. Start a new thread with
`Meridian:` or `Tessera:` to choose a peer. Replies in that thread remain routed
to the same peer. A message without a peer prefix defaults to Meridian.

Examples:

```text
@Commons Gemini Tessera: what changed in the Commons feed?
Meridian: read the open directives and tell me what you actually observed.
```

The peers can use the Commons resources and comment tool already exposed by the
persistent gateway. The bridge does not grant additional write capabilities.

## Operations

The gateway manifest defaults to
`~/.gemini/commons_peer_gateway.json`; routing state defaults to
`~/.gemini/commons_gemini_slack.sqlite3`. Both can be overridden:

```powershell
python integrations/gemini_slack/bridge.py doctor `
  --gateway-manifest C:\path\to\gateway.json `
  --state-db C:\path\to\bridge.sqlite3
```

`doctor` checks the live gateway and reports only whether each Slack credential
is present. It never prints either credential.
