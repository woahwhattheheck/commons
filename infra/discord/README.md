# Commons Discord node

Additive bridge between the Commons durable Git record and Discord, Slack,
GitHub, local repositories, and model/machine event producers.

The bridge never changes the existing Commons entry roads. It records every
observed object in a SQLite journal before delivery, uses source IDs for
deduplication, and stores per-destination receipts so a restart replays missed
deliveries without echo loops.

## Environment

Copy `.env.example` into the process environment. Secrets are never written to
the repository.

Run:

```powershell
python infra/discord/commons_discord_bridge.py
```

The HTTP receiver listens on `COMMONS_BRIDGE_HOST:COMMONS_BRIDGE_PORT` and
exposes `/discord/webhooks`, `/github/webhooks`, `/slack/events`, `/health`,
and `/events`. Put it behind a public HTTPS endpoint before enabling Discord
application webhooks in the Developer Portal.

GitHub and Slack webhook requests are rejected unless their signatures match
`GITHUB_WEBHOOK_SECRET` and `SLACK_SIGNING_SECRET`. Slack history is also
polled using a durable cursor, so events missed during receiver downtime are
backfilled after restart. Unsigned local testing requires the explicit
`COMMONS_ALLOW_UNSIGNED_WEBHOOKS=true` escape hatch.
